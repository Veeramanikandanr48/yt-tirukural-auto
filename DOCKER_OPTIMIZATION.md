# Docker Image Size Optimization

## Problem
Docker image size was 8.4 GB, exceeding the 4.0 GB limit.

## Solutions Applied

### 1. Multi-Stage Build
- **Builder stage**: Installs dependencies with build tools
- **Runtime stage**: Only includes runtime dependencies
- Reduces final image size by excluding build tools

### 2. .dockerignore File
Excludes from image:
- Generated files (videos, audio)
- Model cache (download at runtime)
- Git files
- Documentation
- Temporary files

### 3. Optimized Dependencies
- Uses `--no-cache-dir` for pip
- Removes apt cache after installation
- Only installs runtime dependencies in final stage

### 4. Model Download at Runtime
- Models are NOT included in image
- Downloaded on first run (cached for subsequent runs)
- Saves several GB

## Expected Size Reduction

**Before:** 8.4 GB
**After:** ~1.5-2.5 GB (estimated)

## Additional Optimizations (if still too large)

### Option 1: Use Alpine Linux Base
```dockerfile
FROM python:3.10-alpine
```
- Smaller base image (~50MB vs ~200MB)
- May need additional packages for some dependencies

### Option 2: Exclude Large Assets
If background images are large, exclude them:
```dockerfile
# In .dockerignore
assets/bg/
```
Then download/use external storage for assets.

### Option 3: Use Pre-built PyTorch CPU Image
```dockerfile
FROM pytorch/pytorch:latest-cpu
```
- Optimized for PyTorch
- May still be large

## Verify Image Size

Build and check size:
```bash
docker build -t thirukural-generator .
docker images | grep thirukural-generator
```

## Runtime Considerations

- First run will download model (~500MB-1GB)
- Model is cached for subsequent runs
- Ensure sufficient disk space on deployment platform

## If Still Exceeding Limit

1. **Check what's taking space:**
   ```bash
   docker run --rm thirukural-generator du -sh /app/*
   ```

2. **Consider:**
   - Using external model storage
   - Streaming assets instead of including
   - Using lighter alternatives for dependencies

---

**The optimized Dockerfile should reduce size significantly!**

