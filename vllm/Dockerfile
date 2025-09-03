FROM vllm/vllm-openai:gptoss

# Install latest vLLM wheel from gpt-oss channel at build time
RUN pip install --pre "vllm==0.10.1+gptoss" \
    --extra-index-url https://wheels.vllm.ai/gpt-oss/ \
    --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
    --no-cache-dir
