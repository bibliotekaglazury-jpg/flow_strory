"use client";
import {
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
} from "@assistant-ui/react";
import type { VideoRecipe, CreativePlan, VideoPlan } from "@ugc/contracts";

export function ChatModeSelector({
  mode,
  onChange,
  disabled,
}: {
  mode: "chat" | "auto";
  onChange: (mode: "chat" | "auto") => void;
  disabled: boolean;
}) {
  return (
    <div className="chat-mode segments" aria-label="Prompt mode">
      <button
        type="button"
        aria-pressed={mode === "chat"}
        disabled={disabled}
        onClick={() => onChange("chat")}
      >
        AI Chat
      </button>
      <button
        type="button"
        aria-pressed={mode === "auto"}
        disabled={disabled}
        onClick={() => onChange("auto")}
      >
        Auto
      </button>
    </div>
  );
}
export function ChatMessage({
  role = "assistant",
}: {
  role?: "user" | "assistant";
}) {
  return (
    <MessagePrimitive.Root className="chat-message" data-role={role}>
      <span className="sr-only">
        {role === "user" ? "You: " : "Assistant: "}
      </span>
      <MessagePrimitive.Parts />
    </MessagePrimitive.Root>
  );
}
function UserChatMessage() {
  return <ChatMessage role="user" />;
}
export function ChatMessages() {
  return (
    <ThreadPrimitive.Viewport
      className="chat-messages"
      aria-label="Conversation"
      role="log"
      aria-live="polite"
    >
      <ThreadPrimitive.Empty>
        <p className="chat-empty">
          What should your video show? Tell me about the product, audience and
          style.
        </p>
      </ThreadPrimitive.Empty>
      <ThreadPrimitive.Messages
        components={{
          UserMessage: UserChatMessage,
          AssistantMessage: ChatMessage,
        }}
      />
    </ThreadPrimitive.Viewport>
  );
}
export function ChatComposer({
  disabled,
  busy,
  onCancel,
}: {
  disabled: boolean;
  busy: boolean;
  onCancel: () => void;
}) {
  return (
    <ComposerPrimitive.Root className="chat-composer">
      <ComposerPrimitive.Input
        aria-label="Message about your video"
        placeholder="Describe the video you have in mind…"
        maxLength={4000}
        rows={2}
        disabled={disabled || busy}
      />
      {busy ? (
        <button type="button" className="text-button" onClick={onCancel}>
          Stop and reset
        </button>
      ) : (
        <ComposerPrimitive.Send className="chat-send" disabled={disabled}>
          Send →
        </ComposerPrimitive.Send>
      )}
    </ComposerPrimitive.Root>
  );
}
export function RecipeSummary({
  recipe,
  concept,
  video,
}: {
  recipe: VideoRecipe;
  concept?: CreativePlan | null;
  video?: VideoPlan | null;
}) {
  const clip = video?.clips[0];
  return (
    <div className="recipe-summary">
      <strong>
        Video plan · {recipe.duration}s · {recipe.aspectRatio} ·{" "}
        {new Intl.DisplayNames(["en"], { type: "language" }).of(
          recipe.language || "en",
        )}{" "}
        · Native audio
      </strong>
      {concept ? (
        <dl>
          {[
            ["Concept", concept.creativeAngle],
            ["Hook", clip?.beats[0]?.action || concept.coreTension],
            ["Story", clip?.visualDirection || recipe.scenes.map((scene) => scene.description).join(" ")],
            ["Script", clip?.spokenScript || recipe.spokenContent?.dialogue || "No spoken dialogue."],
            ["Look", `${concept.visualMode} · ${clip?.camera || recipe.camera}`],
          ].map(([label, text]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{text}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <>
          <p>{recipe.concept}</p>
          {recipe.spokenContent?.required && <p>{recipe.spokenContent.dialogue}</p>}
          <span>{recipe.visualStyle} · {recipe.camera}</span>
        </>
      )}
      {!concept && (
        <details>
          <summary>Review full plan</summary>
          <dl>
            {(
              [
                ["intent", "Video goal"],
                ["subject", "Who appears"],
                ["product", "Product"],
                ["performance", "Delivery"],
                ["audio", "Sound"],
              ] as const
            ).map(([key, label]) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{recipe[key]}</dd>
              </div>
            ))}
          </dl>
          <ol>
            {recipe.scenes.map((scene, i) => (
              <li key={i}>
                {scene.duration}s — {scene.description}
              </li>
            ))}
          </ol>
          <p>Constraints: {recipe.constraints.join("; ") || "None"}</p>
          <p>Avoid: {recipe.negativeRules.join("; ") || "None"}</p>
        </details>
      )}
    </div>
  );
}
export function ApplyRecipeButton({
  disabled,
  busy,
  onClick,
}: {
  disabled: boolean;
  busy: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="recipe-apply"
      disabled={disabled}
      onClick={onClick}
    >
      {busy ? "Applying…" : "Use this concept"}
    </button>
  );
}
