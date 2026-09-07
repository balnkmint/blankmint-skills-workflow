# 远端命令与交付模板

仅在应用补丁、构建或部署阶段读取。下面是 Bash 模板，不是已在用户环境执行的命令。把占位值替换成已确认信息；不知道就先询问。命令应在新 Bash 子 shell 中运行，失败退出子 shell 而不关闭用户登录会话。

## 1. 最小只读检查

```bash
cd /absolute/source/path || exit 1
git branch --show-current
git rev-parse HEAD
git status --short
git diff --stat
```

存在暂存改动时还看 `git diff --cached --stat`。不要打印无关环境变量或敏感配置。对相关文件索取 `sed -n '起始,结束p' 文件`、当前声明和调用者，不索取整个服务器目录。

## 2. 检查后应用单个补丁

```bash
(
set -eu
cd /absolute/source/path
PATCH_FILE=/absolute/patch/path/0001-example.patch
test -f "$PATCH_FILE"
sha256sum "$PATCH_FILE"
# 先与交付摘要核对；自动化时用预先确认的摘要作严格比较。
git apply --check "$PATCH_FILE"
git apply "$PATCH_FILE"
git diff --check
git status --short
)
PATCH_STEP_RET=$?
echo "patch_step_ret=$PATCH_STEP_RET"
```

摘要人工核对应在应用前完成，实际发给用户时可分为“摘要检查”和“应用”两块；需要自动门禁则在 apply 前增加 `test "$(sha256sum "$PATCH_FILE" | cut -d ' ' -f 1)" = "确认过的摘要"`。Mac 本地使用 `shasum -a 256`。

返回非零时停止。补丁已经应用后不要重复执行；先检查源码状态。系列补丁每个步骤成功才继续，记录最后成功编号。

## 3. 保存构建退出码

```bash
(
set +e
set -u
cd /absolute/source/path || exit 1
make ARCH=arm64 -j"$(nproc)" Image 2>&1 | tee /tmp/task-build-01.log
BUILD_CODES=("${PIPESTATUS[@]}")
echo "build_ret=${BUILD_CODES[0]}"
echo "log_ret=${BUILD_CODES[1]}"
if [ "${BUILD_CODES[0]}" -ne 0 ]; then
    exit "${BUILD_CODES[0]}"
fi
test "${BUILD_CODES[1]}" -eq 0 || exit 1
sha256sum arch/arm64/boot/Image
make ARCH=arm64 kernelrelease
)
```

子 shell 的 `set +e` 防止失败管道在保存状态前退出，随后显式检查两个退出码。`PIPESTATUS` 要立即捕获，不能先 echo、grep 或执行别的命令。适配其他项目时替换 make 目标与产物，不默认 ARM64。

使用 `O=` 时配置生成、olddefconfig、构建和产物检查都用同一个明确的输出目录，先检查变量非空。受管理配置片段的更改不会自动应用到现有 `.config`。

## 4. 应用失败后的回传清单

- 失败补丁完整错误、摘要、当前分支和 HEAD。
- `git status --short`，相关文件当前差异（包括暂存区）。
- 失败 hunk 涉及的完整函数及前后上下文。
- 已成功应用的编号；是否重传过同名补丁。

区分：文件不存在、补丁格式损坏、上下文不匹配、已应用、实质代码不同。不要把它们统一归为缩进问题。

## 5. 构建/部署检查重点

- ELF：目标架构、解释器、NEEDED、SONAME、所需符号版本和实际运行库；优先 `file`、`readelf`。
- 对自己构建且可信的程序，可在目标运行环境做依赖解析；不得把 `ldd` 错误用 `|| true` 后当成功。不要只在编译环境验证。
- 文件名不同不一定 ABI 不同；SONAME 相同也不足以独立证明全部 ABI 相容。只在已核实库来源和 ABI 后补软链。
- 先验证候选文件，再备份和替换；不要先覆盖可用程序再发现 GLIBC 不兼容。
- 失败日志回传首个实际错误及必要上下文，不只发最后一行 `make: Error 2`。
