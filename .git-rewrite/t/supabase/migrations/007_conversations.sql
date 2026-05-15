-- Migration 007: Conversations (Phase 4)
--   Persiste el historial de chat del Architect.
-- ============================================================

CREATE TABLE conversations (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                    UUID NOT NULL REFERENCES organizations(id)
                                                       ON DELETE CASCADE,
  user_id                   TEXT,
  workflow_template_id      UUID REFERENCES workflow_templates(id),
  status                    TEXT DEFAULT 'in_progress'
                                              CHECK (status IN ('in_progress','completed','failed')),
  metadata                  JSONB DEFAULT '{}',
  created_at                TIMESTAMPTZ DEFAULT now(),
  updated_at                TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id)
                                                 ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content         TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_conversations_org_status
  ON conversations(org_id, status);
CREATE INDEX idx_conversation_messages_conv
  ON conversation_messages(conversation_id);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "conv_tenant_isolation" ON conversations
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

CREATE POLICY "conv_msg_tenant_isolation" ON conversation_messages
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM conversations c
      WHERE c.id = conversation_messages.conversation_id
        AND c.org_id::text = current_setting('app.org_id', TRUE)
    )
  );
