import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  askChatQuestion,
  createChatSession,
  deleteChatHistory,
  getChatSession,
  listChatSessions,
  queryKeys,
  type ChatMessage,
  type ChatReference,
  type ChatSessionListItem,
  type ChatSupportingData,
} from "../api/runstats";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "../components/StatusViews";
import { formatDateTime, formatSport } from "../lib/formatters";

const starterQuestions = [
  "How much did I run each week?",
  "What is my fastest 5K this year?",
  "Show my longest run with heart-rate details.",
  "What changed after my last sync?",
];

export function ChatAssistantView() {
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const sessions = useQuery({
    queryKey: queryKeys.chat.list({ limit: 50 }),
    queryFn: () => listChatSessions({ limit: 50 }),
  });

  useEffect(() => {
    if (!activeSessionId && sessions.data?.items[0]) {
      setActiveSessionId(sessions.data.items[0].id);
    }
  }, [activeSessionId, sessions.data?.items]);

  const activeSession = useQuery({
    enabled: Boolean(activeSessionId),
    queryKey: activeSessionId
      ? queryKeys.chat.detail(activeSessionId)
      : ["chat", "detail", "none"],
    queryFn: () => getChatSession(activeSessionId ?? ""),
  });

  const createSessionMutation = useMutation({
    mutationFn: () => createChatSession(),
    onSuccess: (session) => {
      setActiveSessionId(session.id);
      void queryClient.invalidateQueries({ queryKey: queryKeys.chat.all });
    },
  });

  const askMutation = useMutation({
    mutationFn: async (message: string) => {
      const sessionId = activeSessionId ?? (await createChatSession()).id;
      setActiveSessionId(sessionId);
      return askChatQuestion(sessionId, message);
    },
    onSuccess: () => {
      setDraft("");
      void queryClient.invalidateQueries({ queryKey: queryKeys.chat.all });
    },
  });

  const deleteHistoryMutation = useMutation({
    mutationFn: deleteChatHistory,
    onSuccess: () => {
      setActiveSessionId(null);
      void queryClient.invalidateQueries({ queryKey: queryKeys.chat.all });
    },
  });

  const canSend = draft.trim().length > 0 && !askMutation.isPending;
  const sessionItems = sessions.data?.items ?? [];
  const messages = activeSession.data?.messages ?? [];

  function sendDraft() {
    const message = draft.trim();
    if (message) {
      askMutation.mutate(message);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Chat Assistant"
        title="Ask your local data"
        actions={
          <div className="page-actions">
            <button
              className="secondary-button"
              disabled={createSessionMutation.isPending}
              onClick={() => createSessionMutation.mutate()}
              type="button"
            >
              New chat
            </button>
            <button
              className="secondary-button"
              disabled={deleteHistoryMutation.isPending || sessionItems.length === 0}
              onClick={() => {
                if (window.confirm("Delete all chat history?")) {
                  deleteHistoryMutation.mutate();
                }
              }}
              type="button"
            >
              Delete history
            </button>
          </div>
        }
      />

      <section className="chat-layout">
        <aside className="data-panel chat-session-panel">
          <div className="panel-heading">
            <h3>Sessions</h3>
            <p>{sessions.data?.total ?? 0} total</p>
          </div>
          {sessions.isLoading ? (
            <LoadingState title="Loading chats" />
          ) : sessions.isError ? (
            <ErrorState error={sessions.error} title="Chat history unavailable" />
          ) : sessionItems.length === 0 ? (
            <EmptyState title="No chats yet" />
          ) : (
            <SessionList
              activeSessionId={activeSessionId}
              onSelect={setActiveSessionId}
              sessions={sessionItems}
            />
          )}
        </aside>

        <section className="data-panel chat-thread-panel">
          {activeSession.isLoading ? (
            <LoadingState title="Loading conversation" />
          ) : activeSession.isError ? (
            <ErrorState error={activeSession.error} title="Conversation unavailable" />
          ) : messages.length === 0 ? (
            <ChatEmptyState onPickStarter={setDraft} />
          ) : (
            <MessageList messages={messages} />
          )}

          {askMutation.isPending ? (
            <div className="chat-message chat-message-assistant" aria-live="polite">
              <p>Answering from approved local tools...</p>
            </div>
          ) : null}

          {askMutation.isError ? (
            <ErrorState error={askMutation.error} title="Chat response unavailable" />
          ) : null}

          <form
            className="chat-composer"
            onSubmit={(event) => {
              event.preventDefault();
              sendDraft();
            }}
          >
            <label htmlFor="chat-message">Message</label>
            <textarea
              id="chat-message"
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <button className="secondary-button" disabled={!canSend} type="submit">
              {askMutation.isPending ? "Sending..." : "Send"}
            </button>
          </form>
        </section>
      </section>
    </>
  );
}

function SessionList({
  activeSessionId,
  onSelect,
  sessions,
}: {
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  sessions: ChatSessionListItem[];
}) {
  return (
    <div className="chat-session-list">
      {sessions.map((session) => (
        <button
          className={
            session.id === activeSessionId
              ? "chat-session-row chat-session-row-active"
              : "chat-session-row"
          }
          key={session.id}
          onClick={() => onSelect(session.id)}
          type="button"
        >
          <strong>{session.title ?? "Untitled chat"}</strong>
          <span>{session.last_message_preview ?? formatDateTime(session.updated_at)}</span>
        </button>
      ))}
    </div>
  );
}

function ChatEmptyState({
  onPickStarter,
}: {
  onPickStarter: (question: string) => void;
}) {
  return (
    <div className="chat-empty">
      <EmptyState title="No messages yet" />
      <div className="starter-grid">
        {starterQuestions.map((question) => (
          <button
            className="secondary-button"
            key={question}
            onClick={() => onPickStarter(question)}
            type="button"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="chat-thread" aria-label="Chat messages">
      {messages.map((message) => (
        <article
          className={`chat-message chat-message-${message.role}`}
          key={message.id}
        >
          <div className="chat-message-heading">
            <strong>{message.role === "user" ? "You" : "RunStats"}</strong>
            <span>{formatDateTime(message.created_at)}</span>
          </div>
          <p>{message.content}</p>
          {message.tool_trace ? (
            <SupportingData supportingData={message.tool_trace} />
          ) : null}
        </article>
      ))}
    </div>
  );
}

function SupportingData({
  supportingData,
}: {
  supportingData: ChatSupportingData;
}) {
  const hasDetails =
    supportingData.metrics.length > 0 ||
    supportingData.time_range ||
    supportingData.references.length > 0 ||
    supportingData.notes.length > 0;

  if (!hasDetails) {
    return null;
  }

  return (
    <div className="chat-supporting-data">
      <dl>
        <div>
          <dt>Rows</dt>
          <dd>{supportingData.row_count}</dd>
        </div>
        <div>
          <dt>Range</dt>
          <dd>{supportingData.time_range ?? "All local data"}</dd>
        </div>
        <div>
          <dt>Metrics</dt>
          <dd>
            {supportingData.metrics.length > 0
              ? supportingData.metrics.map(formatSport).join(", ")
              : "None"}
          </dd>
        </div>
      </dl>

      {supportingData.references.length > 0 ? (
        <div className="chat-reference-list">
          {supportingData.references.map((reference) => (
            <ReferenceLink key={`${reference.type}:${reference.id}`} reference={reference} />
          ))}
        </div>
      ) : null}

      {supportingData.notes.map((note) => (
        <p className="muted-copy" key={note}>
          {note}
        </p>
      ))}
    </div>
  );
}

function ReferenceLink({ reference }: { reference: ChatReference }) {
  return (
    <Link className="status-pill" to={reference.href}>
      {reference.label}
    </Link>
  );
}
