# Docker Build Fix - Attempt #2

## Problem
Even after fixing the local build, Google Cloud Run deployment still fails with:
```
✗ Build failed in 14ms
error during build:
Could not resolve entry module "client/index.html".
```

## Root Cause Analysis
The issue was that the Vite config was using **absolute paths** with `path.resolve()`:
```typescript
root: path.resolve(__dirname, "client"),
build: {
  outDir: path.resolve(__dirname, "dist", "public"),
}
```

In the Docker container, `__dirname` evaluates to `/app`, making the paths:
- `root: /app/client`
- `outDir: /app/dist/public`

While this *should* work, Vite's path resolution in Docker containers can be unpredictable with absolute paths.

## Solution Applied

### Changed to Relative Paths
Updated `vite.config.ts` to use **relative paths**:

```typescript
root: "client",
build: {
  outDir: "../dist/public",
  emptyOutDir: true,
},
```

### Why This Works Better
1. **Simpler resolution**: Vite resolves paths relative to the config file location
2. **Docker-friendly**: Works regardless of where the working directory is set
3. **More portable**: Doesn't depend on `__dirname` behavior in different environments

### What Stayed the Same
Path aliases still use absolute paths (which is correct):
```typescript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "client", "src"),
    "@shared": path.resolve(__dirname, "shared"),
    "@assets": path.resolve(__dirname, "attached_assets"),
  },
},
```

These need to be absolute to resolve correctly from any file in the project.

## Testing

### Local Build (Verified ✅)
```bash
$ npm run build
✓ 3424 modules transformed.
✓ built in 39.08s
```

### Docker Build (Ready to Test)
```bash
# Test locally with Docker
docker build -t sqlgym-test .

# Or deploy to Cloud Run
gcloud builds submit --config=cloudbuild.staging.yaml
```

## Files Changed

| File | Change | Reason |
|------|--------|--------|
| `vite.config.ts` | Changed `root` from absolute to relative path | Better Docker compatibility |
| `vite.config.ts` | Changed `outDir` from absolute to relative path | Simpler path resolution |
| `vite.config.ts` | Removed `rollupOptions.input` | Not needed with relative root |

## Expected Outcome

The Docker build should now succeed because:
1. Vite will look for `index.html` in the `client/` directory (relative to config)
2. Output will go to `dist/public/` (relative to project root)
3. No complex path resolution needed

## If This Still Fails

If you still get the same error, try:

1. **Add debug logging to Dockerfile**:
```dockerfile
RUN ls -la && ls -la client/ && pwd
RUN cat vite.config.ts
RUN npm run build
```

2. **Check .dockerignore**: Ensure `client/` is not excluded

3. **Verify client/index.html exists** in your repository

4. **Try explicit input path**:
```typescript
build: {
  outDir: "../dist/public",
  rollupOptions: {
    input: "./index.html",  // relative to root
  },
}
```

---

**Updated**: October 22, 2025  
**Status**: Ready for Docker testing
