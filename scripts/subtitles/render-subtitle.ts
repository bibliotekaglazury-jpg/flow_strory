// Renders one immutable Subtitle Studio export snapshot through the registered composition.
// User text only ever arrives inside the --input JSON file, never on the command line.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {bundle} from '@remotion/bundler';
import {getCompositions, openBrowser, renderMedia, renderStill} from '@remotion/renderer';
import sharp from 'sharp';
import {SUBTITLE_COMPOSITION_ID, SUBTITLE_FPS, subtitleDimensions} from '../../packages/video-templates/src/subtitles/types';

const packageRoot = path.resolve('packages/video-templates');

// The renderer's browser needs an HTTP source; a loopback server on a random port keeps the
// video private to this process and works the same for local and object storage.
function serveSource(file: string) {
  return new Promise<{url: string; close: () => void}>((resolve) => {
    const size = fs.statSync(file).size;
    const server = http.createServer((req, res) => {
      if (req.url !== '/source.mp4') {
        res.writeHead(404);
        res.end();
        return;
      }
      const range = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
      let start = 0;
      let end = size - 1;
      if (range) {
        if (range[1]) start = Number(range[1]);
        if (range[2]) end = Math.min(Number(range[2]), size - 1);
        res.writeHead(206, {'Content-Type': 'video/mp4', 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1, 'Accept-Ranges': 'bytes'});
      } else {
        res.writeHead(200, {'Content-Type': 'video/mp4', 'Content-Length': size, 'Accept-Ranges': 'bytes'});
      }
      if (req.method === 'HEAD') {
        res.end();
        return;
      }
      fs.createReadStream(file, {start, end}).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => {
      const address = server.address() as {port: number};
      resolve({url: `http://127.0.0.1:${address.port}/source.mp4`, close: () => server.close()});
    });
  });
}

async function main() {
  const {values} = parseArgs({options: {input: {type: 'string'}, output: {type: 'string'}}});
  if (!values.input || !values.output || !values.output.endsWith('.mp4')) throw Error('Input JSON and output MP4 paths required');
  const job = JSON.parse(fs.readFileSync(values.input, 'utf8'));
  const size = subtitleDimensions[job.aspectRatio as keyof typeof subtitleDimensions];
  if (!size) throw Error('Unsupported aspect ratio');
  if (typeof job.durationMs !== 'number' || job.durationMs < 1000 || job.durationMs > 30 * 60 * 1000) throw Error('Unsupported duration');
  if (typeof job.sourcePath !== 'string' || !path.isAbsolute(job.sourcePath) || !fs.statSync(job.sourcePath).isFile()) throw Error('Source must be a local regular file');
  const durationInFrames = Math.max(1, Math.ceil((job.durationMs / 1000) * SUBTITLE_FPS));
  const source = await serveSource(job.sourcePath);
  const props = {...job.props, sourceUrl: source.url, muted: false};
  const serveUrl = await bundle({entryPoint: path.join(packageRoot, 'src/root.tsx'), publicDir: path.join(packageRoot, 'public')});
  const browser = await openBrowser('chrome', {browserExecutable: process.env.REMOTION_BROWSER_EXECUTABLE || undefined});
  try {
    const compositions = await getCompositions(serveUrl, {puppeteerInstance: browser, inputProps: props});
    const registered = compositions.find((c) => c.id === SUBTITLE_COMPOSITION_ID);
    if (!registered) throw Error('Composition not registered');
    const composition = {...registered, ...size, durationInFrames, props};
    const errors: string[] = [];
    const common = {
      serveUrl,
      composition,
      inputProps: props,
      puppeteerInstance: browser,
      onBrowserLog: (log: {type: string; text: string}) => {
        if (log.type === 'error') errors.push(log.text);
      },
      timeoutInMilliseconds: 120_000,
    };
    fs.mkdirSync(path.dirname(values.output), {recursive: true});
    const still = await renderStill({...common, frame: Math.min(SUBTITLE_FPS, durationInFrames - 1), imageFormat: 'png'});
    await sharp(still.buffer).webp({quality: 88}).toFile(values.output.replace(/\.mp4$/, '.webp'));
    let last = -1;
    await renderMedia({
      ...common,
      codec: 'h264',
      outputLocation: values.output,
      concurrency: 2,
      crf: 23,
      onProgress: (progress) => {
        // Progress lines are the only stdout JSON the worker trusts; they come from real frames.
        const percent = Math.floor(progress.progress * 100);
        if (percent !== last) {
          last = percent;
          console.log(JSON.stringify({progress: percent}));
        }
      },
    });
    if (errors.length) throw Error(`Browser errors: ${errors.join('; ')}`);
  } finally {
    source.close();
    await browser.close({silent: true});
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
