CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS emails (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL,
  provider_id text NOT NULL,
  thread_id   text,
  sent_at     timestamptz NOT NULL,
  sender_hash bytea,
  labels      text[],
  ciphertext  bytea NOT NULL,
  nonce       bytea NOT NULL,
  key_id      text NOT NULL,
  UNIQUE (user_id, provider_id)
);

CREATE TABLE IF NOT EXISTS email_chunks (
  id          bigserial PRIMARY KEY,
  email_id    uuid NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL,
  chunk_idx   int NOT NULL,
  embedding   vector(384) NOT NULL,
  embed_model text NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
  ON email_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_user_idx ON email_chunks (user_id);