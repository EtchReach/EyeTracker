# Developer's Manual

This manual provides information for debugging, profiling, releasing and notes for future development.

## Quick Reference

| Task | Command/Process |
|------|----------------|
| Run application locally from cli | `python main.py` |
| Run older pre-app version | `cd app/pre_app_core` `python pupil_fitter.py` |
| Profile pupil tracking computation | `python -m app.core.profiler` |
| Build project locally | `python scripts/build.py` |
| Create release | Follow the [Release Process](#releasing) |

*run all commands from root of proj, i.e. Eyetracker

## Profiling

To profile the software workload and identify performance bottlenecks:

```bash
python -m app.core.profiler
```

Run this command from the project root directory. The profiler will help identify which functions are consuming the most computational resources.

## Releasing

Follow these steps to create a new release:

### 1. Commit Changes
Save your changes to git:
```bash
git add .
git commit -m "your_commit_message"
```

### 2. Local Testing
Build and test the application locally:
```bash
python script/build.py
```
**Important:** Test the generated executable thoroughly before proceeding.

### 3. CI/CD Testing
Test the build on the GitHub workflow to ensure it passes all automated tests.

### 4. Version Tagging
Tag the commit with the appropriate version number:
```bash
git tag v1.x.x
```

### 5. Deploy
Push your changes and tags:
```bash
git push
git push --tags
```

## Debugging

### Google Sheets

For local development, configure Google Sheets export with a `.env` file in the project root. The app still supports the existing per-user `config.json`, but `.env` now overrides the `google_sheets` settings.

Use `.env.example` as the template:

```env
EYETRACKER_GOOGLE_SHEETS_ENABLED=true
EYETRACKER_GOOGLE_SHEETS_CREDENTIALS_PATH=./service-account.json
EYETRACKER_GOOGLE_SHEETS_SPREADSHEET_ID=your_google_sheet_id
EYETRACKER_GOOGLE_SHEETS_WORKSHEET_NAME=Sheet1
```

Keep the Google service account JSON file out of git and point `EYETRACKER_GOOGLE_SHEETS_CREDENTIALS_PATH` at it.

### Performance Issues

#### Problem: Sluggish Camera Feed / Low FPS

**Root Cause:** There's an inherent trade-off between processing speed and accuracy. The current release prioritizes accuracy, which impacts performance.

**Primary Bottlenecks:**
- `get_darkest_area()` - Called 3 times per frame
- `optimize_contours_by_angle()` - Called 3 times per frame
- Multiple matrix operations in both functions

#### Optimization Options

The following optimized functions are available as alternatives:

##### `optimize_contours_by_angle_vectorised()`
- **Performance:** Significantly faster than the original brute-force method
- **Implementation:** Uses NumPy vector calculations, batching, and dynamic filtering
- **Trade-off:** Higher probability of value differences between adjacent frames, resulting in increased jitter in the final fitted ellipse

##### `get_darkest_area_vectorised()`
- **Performance:** Much faster than the original implementation
- **Implementation:** Uses NumPy vector optimizations, trading memory for speed
- **Accuracy:** Similar to the original method

##### `get_darkest_area_optimised()`
- **Performance:** Significantly faster than other implementations
- **Implementation:** Uses `cv2.blur()` to average color intensity of binary kernels instead of cell-by-cell checking
- **Trade-off:** Provides estimates rather than exact calculations, resulting in some accuracy loss

#### Recommendations

1. **For Production:** Use the current accurate configuration unless performance is critically impacted
2. **For Performance-Critical Applications:** Consider `get_darkest_area_vectorised()` as it maintains accuracy while improving speed
3. **For Real-Time Applications:** Use `get_darkest_area_optimised()` if slight accuracy reduction is acceptable
4. **Hybrid Approach:** Implement dynamic switching between methods based on system load or user preferences

### Troubleshooting Tips

- Monitor frame rates using the profiler to identify when performance degradation occurs
- Test different optimization combinations to find the best balance for your specific use case
- Consider implementing performance monitoring in production to automatically switch optimization levels

## Development Workflow

1. **Before Making Changes:** Run the profiler to establish baseline performance metrics
2. **During Development:** Test changes locally using the build script
3. **Before Committing:** Ensure all tests pass and performance hasn't significantly degraded
4. **After Release:** Monitor application performance and user feedback

## Additional Resources

- Performance profiling results are saved in the project logs
- Build artifacts are generated in the `dist/` directory
- CI/CD logs provide detailed information about automated testing results


## Future Notes

1. Might want to add some form of face detection to auto crop the frame to leave only the pupil as the darkest area.
