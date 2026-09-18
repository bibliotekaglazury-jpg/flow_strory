"use client";
import { useEffect, useRef, useState } from "react";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  useExternalStoreRuntime,
  type AppendMessage,
  type ThreadMessageLike,
} from "@assistant-ui/react";
import type { AppliedRecipe, ChatSession, CreativeInput } from "@ugc/contracts";
import { getServices } from "@/services";
import {
  ApplyRecipeButton,
  ChatComposer,
  ChatMessages,
  RecipeSummary,
} from "./chat-parts";

const storageKey = "storyflow-chat-session-v1";
export function VideoChat({
  draft,
  disabled,
  onApply,
  onWorking,
}: {
  draft: CreativeInput;
  disabled: boolean;
  onApply: (result: AppliedRecipe) => Promise<void>;
  onWorking?: (working: boolean) => void;
}) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null),
    [applied, setApplied] = useState(false);
  const current = useRef<ChatSession | null>(null),
    operation = useRef(0),
    lock = useRef(false);
  const draftRef = useRef(draft);
  const nextIntent = useRef<"message" | "change_concept">("message");
  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);
  function remember(value: ChatSession | null) {
    current.current = value;
    setSession(value);
    if (value) sessionStorage.setItem(storageKey, value.id);
    else sessionStorage.removeItem(storageKey);
  }
  useEffect(() => {
    let active = true;
    const saved = sessionStorage.getItem(storageKey);
    (saved ? getServices().chat.get(saved) : Promise.resolve(null))
      .then((value) => {
        if (!active) return;
        // A page reload only resumes a turn still generating; a finished or
        // idle conversation does not survive a refresh, so context always
        // starts clean unless something was actually in flight.
        if (value && value.status !== "responding") {
          sessionStorage.removeItem(storageKey);
          value = null;
        }
        current.current = value;
        setSession(value);
      })
      .catch(() => {
        if (active) {
          sessionStorage.removeItem(storageKey);
          setError(
            "Previous conversation is unavailable. Send a message to start again.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  // Recover a turn already running when the page was refreshed.
  useEffect(() => {
    if (session?.status !== "responding" || busy) return;
    const timer = setInterval(() => {
      getServices()
        .chat.get(session.id)
        .then(remember)
        .catch(() => setError("Could not refresh the conversation."));
    }, 2000);
    return () => clearInterval(timer);
  }, [session?.id, session?.status, busy]);
  async function onNew(message: AppendMessage) {
    if (lock.current || disabled) return;
    const text = message.content
      .filter((p) => p.type === "text")
      .map((p) => p.text)
      .join("\n");
    if (!text.trim()) return;
    lock.current = true;
    setBusy(true);
    setError(null);
    setApplied(false);
    const version = ++operation.current;
    try {
      const service = getServices().chat;
      const item = current.current || (await service.create());
      if (version !== operation.current) {
        await service.delete(item.id);
        return;
      }
      remember(item);
      const {
        templateId,
        inputAssets,
        duration,
        aspectRatio,
        productUrl,
        brief,
        language,
      } = draftRef.current;
      const next = await service.send(item.id, {
        text,
        intent: nextIntent.current,
        context: {
          templateId,
          inputAssets,
          duration,
          aspectRatio,
          productUrl,
          brief,
          ...(language ? { language } : {}),
        },
      });
      if (version === operation.current) {
        nextIntent.current = "message";
        remember(next);
      }
    } catch (e) {
      if (version === operation.current) {
        setError((e as Error).message);
        runtime.thread.composer.setText(text);
        if (current.current)
          getServices()
            .chat.get(current.current.id)
            .then(remember)
            .catch(() => {});
      }
    } finally {
      if (version === operation.current) {
        lock.current = false;
        setBusy(false);
      }
    }
  }
  async function reset() {
    const item = current.current;
    ++operation.current;
    try {
      if (item) await getServices().chat.delete(item.id);
      remember(null);
      setError(null);
      setApplied(false);
      nextIntent.current = "message";
    } catch (e) {
      setError((e as Error).message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const running = busy || session?.status === "responding";
  // The workspace owns the full-block loader, so the chat reports when the director is
  // actually working; a text line alone read as nothing happening.
  const working = running || applying;
  // A single generation can take well over a minute with no server progress events; a
  // live counter is the only honest way to show the turn is alive, not frozen. Stage
  // wording only orders what the director actually does (read, draft, finish) and never
  // claims a specific step is running right now.
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  useEffect(() => {
    if (!running) return;
    const startedAt = Date.now();
    const timer = setInterval(() => {
      setElapsedSeconds(Math.round((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => {
      clearInterval(timer);
      setElapsedSeconds(0);
    };
  }, [running]);
  const thinkingStage =
    elapsedSeconds < 20
      ? "Reading your brief…"
      : elapsedSeconds < 45
        ? "Writing concepts…"
        : "Finishing the script…";
  useEffect(() => {
    onWorking?.(working);
  }, [working, onWorking]);
  const runtime = useExternalStoreRuntime({
    messages: session?.messages || [],
    isRunning: running,
    convertMessage: (message): ThreadMessageLike => ({
      id: message.id,
      role: message.role,
      content: [{ type: "text", text: message.text }],
      createdAt: new Date(message.createdAt),
    }),
    onNew,
    onCancel: reset,
  });
  async function apply() {
    if (!session || applying || disabled) return;
    setApplying(true);
    setError(null);
    const original = JSON.stringify(draft);
    try {
      const result = await getServices().chat.apply(session.id, {
        revision: session.revision,
        creative: {
          ...draft,
          brief: session.answer?.recipe?.concept || draft.brief,
        },
      });
      if (JSON.stringify(draftRef.current) !== original)
        throw new Error(
          "Inputs changed. Review the recipe and apply it again.",
        );
      await onApply(result);
      setApplied(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setApplying(false);
    }
  }
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadPrimitive.Root
        className="video-chat"
        aria-label="Video planning chat"
      >
        <div className="chat-heading">
          <span>Creative Director{session?.simulated ? " · Demo" : ""}</span>
          {session && (
            <button
              className="text-button"
              type="button"
              disabled={applying}
              onClick={() => void reset()}
            >
              Reset conversation
            </button>
          )}
        </div>
        {loading ? (
          <p role="status">Loading conversation…</p>
        ) : (
          <ChatMessages />
        )}
        <ChatComposer
          busy={running}
          disabled={disabled || loading || applying}
          onCancel={() => void reset()}
        />
        {running && (
          <p role="status" className="form-note chat-thinking">
            <span className="chat-thinking-dot" aria-hidden="true" />
            {thinkingStage} <span className="chat-thinking-seconds">{elapsedSeconds}s</span>
          </p>
        )}
        {session?.simulated && (
          <p className="form-note">
            Demo conversation: replies are simulated, not generated by AI.
          </p>
        )}
        {session?.answer?.clarificationQuestion &&
          session.answer.clarificationQuestion !==
            session.answer.assistantMessage && (
            <p>{session.answer.clarificationQuestion}</p>
          )}
        {session?.answer?.recipe && !running && (
          <>
            <RecipeSummary
              recipe={session.answer.recipe}
              concept={session.answer.creativePlan}
              video={session.answer.videoPlan}
            />
            <div className="recipe-actions">
              <ApplyRecipeButton
                disabled={disabled || applying}
                busy={applying}
                onClick={() => void apply()}
              />
              <button
                type="button"
                className="text-button"
                disabled={disabled || applying}
                onClick={() => {
                  nextIntent.current = "change_concept";
                  runtime.thread.composer.setText("Change the concept: ");
                  document
                    .querySelector<HTMLTextAreaElement>(
                      '[aria-label="Message about your video"]',
                    )
                    ?.focus();
                }}
              >
                Change concept
              </button>
              <span>
                {applied
                  ? "Applied. Review your prompt and estimate below."
                  : "Applies a concept; does not generate or spend video credits."}
              </span>
            </div>
          </>
        )}
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
      </ThreadPrimitive.Root>
    </AssistantRuntimeProvider>
  );
}
