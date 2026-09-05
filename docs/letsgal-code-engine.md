# LetsGal 代码层适配

`letsgal` 输出的是可粘贴到 LetsGal Studio Ren'Py 风格代码视图的纯文本，
不是剧本 JSON，也不维护 LetsGal 内部 UUID。

## 表格列约定

- `Background` 和 `Event` 共用 `SceneGenerator`，输出 `scene`；同一行不能同时填写。
- `Character`/`Sprite` 输出 `show`，`SpriteCommand` 或 `CharacterCommand` 只接受显示/隐藏。
  角色已经在场时仍然重复输出 `show`，由 Studio 负责更新，不暴露 `update` 列。
- `Name` + `Text` 输出 `Name "Text"`；没有 `Name` 时输出旁白。
- `Music` 和 `Sound` 由 `AudioGenerator` 处理；`Ambience` 有独立生成器和独立循环默认。
  LetsGal 代码语法没有独立的 ambience 关键字，因此 ambience 落为 `play sound ... loop`。
- `Voice` 直接按单元格中的路径输出 `play voice <path>`，不经过资源 UUID 翻译。
- `Volume=80` 输出 `volume 80%`；`AudioFade=0.5` 输出 `fadein 0.5`，停止时输出 `fadeout 0.5`。
- `Pause` 支持秒数、`500ms` 和 `hard`/`点击`（后两者输出无参数的 `pause`）。

低频代码层指令可将 `Name` 填为 `code` 或 `letsgal`，把整行代码放在 `Text` 中。

## 项目默认值

`LetsGalConfig` 提供以下默认值，可在配置文件的 `engine` 段覆盖：

- `default_transition`
- `default_transition_duration`
- `default_transition_wait`
- `music_loop`
- `ambience_loop`
- `sound_loop`

当前实现只依赖 LetsGal 官方代码视图支持的常用语法；复杂 Block 仍应在 Studio
属性面板中调整。
