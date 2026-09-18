import type {
  CreativePlan,
  ChatService,
  ChatSession,
  Services,
  VideoRecipe,
} from "@ugc/contracts";
import { ServiceError } from "./http";

export function createMockChat(
  persist: boolean,
  prompts: Services["prompts"],
): ChatService {
  const key = "storyflow-demo-chat-v2";
  let sessions: Record<string, ChatSession> = {};
  if (persist && typeof window !== "undefined") {
    try {
      sessions = JSON.parse(localStorage.getItem(key) || "{}");
    } catch {
      /* No saved demo. */
    }
  }
  const save = () => {
    if (persist && typeof window !== "undefined")
      localStorage.setItem(key, JSON.stringify(sessions));
  };
  const get = (id: string) => {
    if (!sessions[id])
      throw new ServiceError("CHAT_NOT_FOUND", "Conversation is unavailable.");
    return structuredClone(sessions[id]);
  };
  return {
    async create() {
      const id = crypto.randomUUID(),
        date = new Date().toISOString();
      sessions[id] = {
        id,
        messages: [],
        answer: null,
        revision: 0,
        status: "idle",
        simulated: true,
        createdAt: date,
        updatedAt: date,
      };
      save();
      return get(id);
    },
    async get(id) {
      return get(id);
    },
    async messages(id) {
      return get(id).messages;
    },
    async delete(id) {
      get(id);
      delete sessions[id];
      save();
      return { deleted: true };
    },
    async send(id, { text, context, intent }) {
      const session = get(id);
      if (!text.trim() || text.length > 4000)
        throw new ServiceError(
          "INVALID_INPUT",
          "Enter up to 4,000 characters.",
        );
      if (session.messages.length >= 40)
        throw new ServiceError(
          "CHAT_LIMIT",
          "Start a new conversation to continue.",
        );
      const duration = 15;
      const language = /niemieck|german|deutsch/i.test(text)
        ? "de"
        : /zrób|polsk|dziewczyna|krem/i.test(text)
          ? "pl"
          : "en";
      const dialogue = {
        pl: "Spójrz na ten produkt. Zobacz, jak wygląda z bliska. Poznaj naszą kolekcję.",
        de: "Schau dir dieses Produkt an. Entdecke unsere Kollektion.",
        en: "Take a closer look at this product. Explore our collection.",
      }[language];
      const recipe: VideoRecipe = {
        language,
        spokenContent: { required: true, language, dialogue },
        intent: "Product showcase",
        concept: text.slice(0, 1500),
        duration,
        aspectRatio: context.aspectRatio,
        qualityTier: "auto",
        subject: "A scripted creator",
        product: "Your supplied product",
        visualStyle: "Natural daylight",
        camera: "Handheld with product close-ups",
        performance: "Conversational delivery",
        scenes: [{ duration, description: text.slice(0, 1500) }],
        audio: "Natural voice, no music",
        constraints: ["Preserve product identity"],
        negativeRules: ["Unsubstantiated claims"],
      };
      const assistantMessage =
        "Demo concept ready. Review it, then apply it to your video.";
      session.messages.push(
        {
          id: crypto.randomUUID(),
          role: "user",
          text,
          createdAt: new Date().toISOString(),
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: assistantMessage,
          createdAt: new Date().toISOString(),
        },
      );
      session.answer = {
        assistantMessage,
        needsMoreInformation: false,
        clarificationQuestion: null,
        recipe,
        creativePlan: {
          creativeMechanism: intent === "change_concept" ? "demo-reversed-expectation" : "demo-observation",
          objective: recipe.intent,
          audience: "Interested customers",
          offer: recipe.product,
          coreTension: "Seeing how the offer fits everyday life",
          creativeAngle: recipe.concept,
          selectedFormat: (context.templateId === "auto"
            ? "ugc_review"
            : context.templateId) as CreativePlan["selectedFormat"],
          hookStrategy: "demonstration",
          tone: "Conversational",
          visualMode: recipe.visualStyle,
          language,
          spokenLanguage: language,
          characterConcepts: [recipe.subject],
          productPresentation: recipe.product,
          audioDirection: recipe.audio,
          confidence: 0.8,
        },
        videoPlan: {
          duration: 15,
          aspectRatio: context.aspectRatio,
          language,
          spokenLanguage: language,
          continuity: "One continuous shot",
          characters: [recipe.subject],
          productRules: recipe.constraints,
          constraints: [],
          negativeRules: [],
          clips: [
            {
              start: 0,
              end: 15,
              role: "main",
              narrativePurpose: recipe.intent,
              visualDirection: recipe.concept,
              spokenScript: dialogue,
              camera: recipe.camera,
              performance: recipe.performance,
              audio: {
                native: true,
                speechRequired: true,
                voiceTone: "Natural",
                ambience: "Quiet room",
                music: null,
              },
              beats: [],
            },
          ],
        },
      };
      session.revision++;
      session.updatedAt = new Date().toISOString();
      sessions[id] = session;
      save();
      return get(id);
    },
    async apply(id, { revision, creative }) {
      const session = get(id),
        recipe = session.answer?.recipe;
      if (!recipe || revision !== session.revision)
        throw new ServiceError(
          "STALE_RECIPE",
          "Review the latest recipe first.",
        );
      const next = {
        ...creative,
        templateId:
          session.answer?.creativePlan?.selectedFormat || creative.templateId,
        brief: recipe.concept,
        language: recipe.language,
        duration: recipe.duration,
        aspectRatio: recipe.aspectRatio,
      };
      const prompt = await prompts.generate(next);
      return {
        creative: next,
        prompt: {
          ...prompt,
          prompt: [
            prompt.prompt,
            `Spoken language: ${recipe.language}`,
            `Exact dialogue: ${recipe.spokenContent?.dialogue ?? ""}`,
            "Generate native audio with the video.",
          ].join("\n"),
        },
      };
    },
  };
}
