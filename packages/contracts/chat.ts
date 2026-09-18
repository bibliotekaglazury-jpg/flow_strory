import type {
  CreativeInput,
  PromptResult,
  AspectRatio,
  InputAssets,
} from "./index";

export interface VideoRecipe {
  language: string;
  spokenContent: {
    required: boolean;
    language: string;
    dialogue: string;
  } | null;
  intent: string;
  concept: string;
  duration: 15 | 20 | 30;
  aspectRatio: AspectRatio;
  qualityTier: "auto";
  subject: string;
  product: string;
  visualStyle: string;
  camera: string;
  performance: string;
  scenes: { duration: number; description: string }[];
  audio: string;
  constraints: string[];
  negativeRules: string[];
}
export interface CreativePlan {
  creativeMechanism?: string | null;
  objective: string;
  audience: string;
  offer: string;
  coreTension: string;
  creativeAngle: string;
  selectedFormat:
    | "ugc_review"
    | "product_unboxing"
    | "problem_solution"
    | "product_demo"
    | "testimonial"
    | "trending_style"
    | "hook_cta"
    | "before_after"
    | "self_presentation";
  hookStrategy:
    | "verbal"
    | "visual"
    | "situational"
    | "emotional"
    | "curiosity"
    | "contradiction"
    | "demonstration"
    | "pattern_interrupt";
  tone: string;
  visualMode: string;
  language: string;
  spokenLanguage: string;
  characterConcepts: string[];
  productPresentation: string;
  audioDirection: string;
  confidence: number;
}
export interface VideoPlan {
  duration: 15;
  aspectRatio: AspectRatio;
  language: string;
  spokenLanguage: string;
  continuity: string;
  characters: string[];
  productRules: string[];
  constraints: string[];
  negativeRules: string[];
  clips: {
    start: 0;
    end: 15;
    role: string;
    narrativePurpose: string;
    visualDirection: string;
    spokenScript: string;
    camera: string;
    performance: string;
    audio: {
      native: true;
      speechRequired: boolean;
      voiceTone: string;
      ambience: string;
      music: string | null;
    };
    beats: { start: number; end: number; purpose: string; action: string }[];
  }[];
}
export interface RecipeAnswer {
  creativePlan?: CreativePlan | null;
  videoPlan?: VideoPlan | null;
  assistantMessage: string;
  needsMoreInformation: boolean;
  clarificationQuestion: string | null;
  recipe: VideoRecipe | null;
}
export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
}
export interface ChatSession {
  id: string;
  messages: ChatMessageData[];
  answer: RecipeAnswer | null;
  revision: number;
  status: "idle" | "responding";
  simulated: boolean;
  createdAt: string;
  updatedAt: string;
}
export interface ChatContext {
  productUrl?: string;
  brief?: string;
  templateId: string;
  inputAssets: InputAssets;
  duration: number;
  aspectRatio: AspectRatio;
  language?: string;
  preferredMechanism?: string;
}
export interface AppliedRecipe {
  creative: CreativeInput;
  prompt: PromptResult;
}
export interface ChatService {
  create(): Promise<ChatSession>;
  get(id: string): Promise<ChatSession>;
  messages(id: string): Promise<ChatMessageData[]>;
  send(
    id: string,
    input: { text: string; context: ChatContext; intent?: "message" | "change_concept" },
  ): Promise<ChatSession>;
  delete(id: string): Promise<{ deleted: boolean }>;
  apply(
    id: string,
    input: { revision: number; creative: CreativeInput },
  ): Promise<AppliedRecipe>;
}
