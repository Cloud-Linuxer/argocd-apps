# Amazon Q Development Rules for ArgoCD GitOps Project

## Project Overview
This is a GitOps-based deployment system using ArgoCD for managing AI agent services built with VLLM (Very Large Language Model). The project follows cloud-native patterns with Kubernetes deployment and automated synchronization.

## Architecture Patterns

### GitOps Structure
- `applications/`: ArgoCD Application definitions for automated deployment
- `manifests/`: Kubernetes manifests organized by service
- `backend/`: Python FastAPI service source code
- All deployments follow declarative configuration pattern

### Service Architecture
- **Backend Service**: FastAPI-based AI agent API server with VLLM integration
- **VLLM Service**: Large language model inference engine (20B parameters)
- **Sample App**: Demonstration/testing application
- Services communicate via HTTP APIs and are deployed as separate Kubernetes workloads

## Code Organization Rules

### Backend Service Structure
```
backend/
├── app.py           # FastAPI main application with lifespan management
├── agent.py         # VLLM client and function calling agent implementation
├── mcp_tools.py     # MCP (Model Context Protocol) compatible tools
├── config.py        # Environment-based configuration management
├── requirements.txt # Python dependencies
└── Dockerfile       # Container build definition
```

### Configuration Management
- **Environment Variables**: All sensitive configuration must use environment variables
- **Pydantic Settings**: Use pydantic-settings for type-safe configuration
- **Required vs Optional**: Mark required environment variables with `Field(...)`
- **Security**: Never hardcode sensitive values (API keys, passwords, URLs)

## Development Guidelines

### Python Code Standards
- **FastAPI**: Use async/await patterns for all API endpoints
- **Type Hints**: All functions must include proper type annotations
- **Pydantic Models**: Use BaseModel for request/response schemas
- **Error Handling**: Implement proper exception handling with meaningful error messages
- **Logging**: Use structured logging with appropriate log levels

### API Design Patterns
```python
# Standard API endpoint pattern
@app.get("/api/endpoint")
async def endpoint_handler() -> ResponseModel:
    try:
        # Implementation
        return ResponseModel(...)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Agent Implementation Rules
- **VLLM Client**: Use httpx.AsyncClient for VLLM API communication
- **Tool System**: Implement tools using the Tool class with proper schemas
- **Function Calling**: Support OpenAI-compatible function calling format
- **Conversation Management**: Maintain conversation history with proper message types

### MCP Tools Standards
- **Tool Registration**: Each tool must have name, description, and parameter schema
- **Async Implementation**: All tool functions must be async
- **Error Handling**: Return meaningful error messages on tool execution failures
- **Resource Cleanup**: Implement proper cleanup for HTTP clients and connections

## Kubernetes Deployment Rules

### Manifest Structure
```yaml
# Standard deployment pattern
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-name
  labels:
    app: service-name
    version: "x.y.z"
spec:
  replicas: 2  # Minimum for HA
  selector:
    matchLabels:
      app: service-name
  template:
    spec:
      containers:
      - name: service-name
        image: ghcr.io/cloud-linuxer/service:version
        envFrom:
        - configMapRef:
            name: service-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Resource Management
- **Resource Limits**: Always define both requests and limits
- **Health Checks**: Implement liveness and readiness probes
- **Configuration**: Use ConfigMaps for non-sensitive configuration
- **Secrets**: Use Kubernetes Secrets for sensitive data
- **Image Pull Secrets**: Use ghcr-secret for private registry access

### ArgoCD Application Pattern
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: service-name
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Cloud-Linuxer/argocd-apps.git
    targetRevision: HEAD
    path: manifests/service-name
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Security Requirements

### Environment Variables
- **Never hardcode**: API keys, passwords, URLs, or sensitive configuration
- **Use .env files**: For local development (ensure .gitignore includes .env)
- **Kubernetes Secrets**: For production sensitive data
- **Validation**: Validate all environment variables at startup

### Container Security
- **Base Images**: Use official, minimal base images
- **Non-root User**: Run containers as non-root user when possible
- **Image Scanning**: Ensure container images are scanned for vulnerabilities
- **Registry Security**: Use private registries with proper authentication

### Network Security
- **Service Mesh**: Consider using service mesh for inter-service communication
- **TLS**: Enable TLS for all external communications
- **Network Policies**: Implement Kubernetes network policies
- **Firewall Rules**: Restrict access to necessary ports only

## Development Workflow

### Code Changes
1. Make changes to source code in `backend/` directory
2. Update version in `manifests/backend/deployment.yaml`
3. Build and push container image to ghcr.io
4. Commit changes to trigger ArgoCD sync

### New Service Addition
1. Create source code directory
2. Add ArgoCD Application in `applications/`
3. Create Kubernetes manifests in `manifests/service-name/`
4. Follow naming conventions and resource patterns

### Configuration Updates
1. Update ConfigMap in manifests
2. Ensure environment variables are properly documented
3. Test configuration changes in development environment
4. Deploy via GitOps workflow

## Monitoring and Observability

### Health Checks
- **Endpoint**: `/health` for all services
- **Kubernetes Probes**: Implement both liveness and readiness probes
- **Timeout Configuration**: Set appropriate timeout values

### Logging
- **Structured Logging**: Use JSON format for production logs
- **Log Levels**: Use appropriate log levels (DEBUG, INFO, WARN, ERROR)
- **Correlation IDs**: Include request IDs for tracing
- **Security**: Never log sensitive information

### Metrics
- **Application Metrics**: Expose Prometheus-compatible metrics
- **Resource Metrics**: Monitor CPU, memory, and network usage
- **Business Metrics**: Track API usage, response times, error rates

## Performance Guidelines

### VLLM Integration
- **Connection Pooling**: Use persistent HTTP connections
- **Timeout Management**: Set appropriate timeouts for model inference
- **Rate Limiting**: Implement rate limiting for API endpoints
- **Caching**: Cache model responses when appropriate

### Resource Optimization
- **Memory Management**: Monitor memory usage for large model operations
- **CPU Allocation**: Allocate sufficient CPU for inference workloads
- **Horizontal Scaling**: Design for horizontal pod autoscaling
- **Load Balancing**: Use Kubernetes services for load distribution

## Error Handling Patterns

### API Error Responses
```python
# Standard error response pattern
try:
    result = await some_operation()
    return {"success": True, "data": result}
except ValidationError as e:
    raise HTTPException(status_code=400, detail=f"Validation error: {e}")
except ConnectionError as e:
    raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Tool Execution Error Handling
- **Graceful Degradation**: Continue operation when non-critical tools fail
- **Retry Logic**: Implement exponential backoff for transient failures
- **Circuit Breaker**: Prevent cascade failures in tool chains
- **Fallback Mechanisms**: Provide alternative approaches when tools fail

## Testing Guidelines

### Unit Testing
- Test all tool implementations independently
- Mock external dependencies (VLLM API, HTTP endpoints)
- Validate configuration loading and environment variable handling
- Test error scenarios and edge cases

### Integration Testing
- Test complete agent workflows
- Validate ArgoCD application deployments
- Test service-to-service communication
- Verify health check endpoints

### Load Testing
- Test VLLM API performance under load
- Validate Kubernetes resource limits
- Test auto-scaling behavior
- Monitor memory usage during inference

## Deployment Best Practices

### Version Management
- **Semantic Versioning**: Use semantic versioning for all services
- **Image Tags**: Never use 'latest' tag in production
- **Rollback Strategy**: Maintain ability to rollback to previous versions
- **Change Documentation**: Document all version changes

### Environment Promotion
- **Development**: Local development with .env files
- **Staging**: Kubernetes deployment with ConfigMaps
- **Production**: Full GitOps deployment with proper secrets management
- **Configuration Drift**: Monitor for configuration differences between environments

This rule set ensures consistent development practices, security compliance, and operational excellence for the ArgoCD GitOps AI agent project.