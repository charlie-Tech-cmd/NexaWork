import { useEffect, useRef, useState } from "react";
import { Icon } from "../Icon";

type DemoMessage = {
  id: number;
  initials: string;
  name: string;
  time: string;
  tone: string;
  text: string;
  file?: boolean;
};
const initialMessages: DemoMessage[] = [
  {
    id: 1,
    initials: "AO",
    name: "Amara Okafor",
    time: "9:41 AM",
    tone: "blue",
    text: "The launch brief is ready. Everything we discussed, in one place.",
    file: true,
  },
  {
    id: 2,
    initials: "AM",
    name: "Alex Morgan",
    time: "9:43 AM",
    tone: "slate",
    text: "Love this direction. I’ll add the review notes here so we can keep the context together.",
  },
  {
    id: 3,
    initials: "RS",
    name: "Riya Shah",
    time: "9:45 AM",
    tone: "warm",
    text: "All set for our next chapter.",
  },
];

function demoReply(text: string) {
  if (/\b(file|files|document|documents|brief|pdf)\b/i.test(text))
    return "Try the Files tab above to explore the sample documents. In a workspace with file sharing enabled, your documents stay with the conversation.";
  if (/\b(hello|hi|hey)\b/i.test(text))
    return "Hello! Welcome to the NexaWork demo. Try sharing an update, or ask about the sample files.";
  return "Thanks for the update! This is a simulated reply. In your workspace, the people in this conversation can read and respond to your messages.";
}

export function DemoConversation({ active }: { active: boolean }) {
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const nextId = useRef(4);
  const composer = useRef<HTMLTextAreaElement>(null);
  const history = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pending === null) return;
    const timer = window.setTimeout(() => {
      const reply: DemoMessage = {
        id: nextId.current++,
        initials: "AM",
        name: "Alex Morgan",
        time: "Demo reply",
        tone: "slate",
        text: demoReply(pending),
      };
      setMessages((current) => [...current, reply].slice(-40));
      setPending(null);
    }, 700);
    return () => window.clearTimeout(timer);
  }, [pending]);

  useEffect(() => {
    if (active && history.current)
      history.current.scrollTop =
        messages === initialMessages ? 0 : history.current.scrollHeight;
  }, [messages, active]);

  function send() {
    const text = draft.trim();
    if (!text || text.length > 500 || pending !== null) return;
    const message: DemoMessage = {
      id: nextId.current++,
      initials: "YO",
      name: "You",
      time: "Just now",
      tone: "blue",
      text,
    };
    setMessages((current) => [...current, message].slice(-40));
    setDraft("");
    setPending(text);
    composer.current?.focus();
  }

  function reset() {
    setPending(null);
    setMessages(initialMessages);
    setDraft("");
    composer.current?.focus();
  }

  return (
    <>
      <div className="demo-day">
        <span />
        Today
        <span />
      </div>
      <div
        ref={history}
        className="demo-history"
        role="log"
        aria-label="Demo conversation"
        aria-relevant="additions"
        tabIndex={0}
      >
        {messages.map((message) => (
          <div className="demo-message" key={message.id}>
            <span
              className={`demo-avatar avatar-${message.tone}`}
              aria-hidden="true"
            >
              {message.initials}
            </span>
            <div className="demo-message-body">
              <p className="demo-message-meta">
                <strong>{message.name}</strong>
                <span>{message.time}</span>
              </p>
              <p>{message.text}</p>
              {message.file && (
                <div className="preview-attachment">
                  <span className="preview-file-icon">
                    <Icon name="file" />
                  </span>
                  <div>
                    <strong>Launch brief.pdf</strong>
                    <span>PDF document · 2.4 MB</span>
                  </div>
                  <Icon name="check" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="demo-reply-status" role="status">
        {pending !== null
          ? "Preparing a simulated reply…"
          : "Demo only · messages stay on this page and clear on refresh."}
      </div>
      <form
        className="demo-composer-note"
        aria-label="Send a demo message"
        onSubmit={(event) => {
          event.preventDefault();
          send();
        }}
      >
        <label className="demo-input-label" htmlFor="demo-message-input">
          Your demo message
        </label>
        <textarea
          ref={composer}
          id="demo-message-input"
          placeholder="Type a message. Try “Hello team!”"
          rows={2}
          maxLength={500}
          value={draft}
          aria-describedby="demo-composer-help"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing &&
              event.nativeEvent.keyCode !== 229
            ) {
              event.preventDefault();
              send();
            }
          }}
        />
        <button
          type="submit"
          aria-label="Send demo message"
          disabled={!draft.trim() || pending !== null}
        >
          <Icon name="arrow" />
        </button>
      </form>
      <div className="demo-composer-help">
        <span id="demo-composer-help">
          Enter to send · Shift + Enter for a new line{" "}
          <span className="demo-character-count">{draft.length}/500</span>
        </span>
        <button type="button" onClick={reset}>
          Reset demo
        </button>
      </div>
    </>
  );
}
