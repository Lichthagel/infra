# Parakeet Redux

This app serves `moondream/parakeet-redux` on the CPU in `sumireko` using Kestrel.
Redux is the CPU-oriented, 178 MB ternary model based on Parakeet TDT 0.6B v3.
It exposes an internal OpenAI-compatible audio transcription API at
`http://parakeet-redux.parakeet-redux.svc.cluster.local:8000/v1/audio/transcriptions`.

LiteLLM registers the `parakeet-redux` transcription model in its GitOps values.
Clients can call it through the usual `/v1/audio/transcriptions` endpoint with
`model=parakeet-redux`.

The pod installs pinned Python packages during startup because this repository
does not build or publish application container images. It needs outbound access
to PyPI, the PyTorch CPU wheel index, and Hugging Face. Hugging Face weights are
cached on the node at `/mnt/data/models/huggingface` so pod restarts do not
redownload them.
