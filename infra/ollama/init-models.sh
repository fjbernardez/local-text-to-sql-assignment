set -eu

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
OLLAMA_MODEL_SQL="${OLLAMA_MODEL_SQL:-qwen2.5-coder:3b}"
OLLAMA_MODEL_NL="${OLLAMA_MODEL_NL:-llama3.2:3b}"

prepare_model() {
  model="$1"
  purpose="$2"

  echo "Pulling ${purpose} model: ${model}"
  ollama pull "${model}"

  echo "Preloading ${purpose} model: ${model}"
  ollama run "${model}" "Return only the word READY"

  echo "${purpose} model ready: ${model}"
}

echo "Waiting for Ollama at ${OLLAMA_HOST}..."

until ollama list > /dev/null 2>&1; do
  echo "Waiting for Ollama..."
  sleep 2
done

echo "Ollama is available."

prepare_model "${OLLAMA_MODEL_SQL}" "SQL"
prepare_model "${OLLAMA_MODEL_NL}" "natural language"
