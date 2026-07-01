<h1 align="center">Jellyfin Web</h1>
<h3 align="center">Part of the <a href="https://jellyfin.org">Jellyfin Project</a></h3>

## Currently Installed PRs

The following PRs are automatically merged into this fork:

- [Upstream PR #5011](https://github.com/jellyfin/jellyfin-web/pull/5011)
- [Upstream PR #6348](https://github.com/jellyfin/jellyfin-web/pull/6348)
- [Upstream PR #6488](https://github.com/jellyfin/jellyfin-web/pull/6488)
- [Upstream PR #7058](https://github.com/jellyfin/jellyfin-web/pull/7058)
- [Upstream PR #7090](https://github.com/jellyfin/jellyfin-web/pull/7090)
- [Upstream PR #7307](https://github.com/jellyfin/jellyfin-web/pull/7307)
- [Upstream PR #7440](https://github.com/jellyfin/jellyfin-web/pull/7440)
- [Upstream PR #7455](https://github.com/jellyfin/jellyfin-web/pull/7455)
- [Upstream PR #7473](https://github.com/jellyfin/jellyfin-web/pull/7473)
- [Upstream PR #7478](https://github.com/jellyfin/jellyfin-web/pull/7478)
- [Upstream PR #7487](https://github.com/jellyfin/jellyfin-web/pull/7487)
- [Upstream PR #7588](https://github.com/jellyfin/jellyfin-web/pull/7588)
- [Upstream PR #7615](https://github.com/jellyfin/jellyfin-web/pull/7615)
- [Upstream PR #7627](https://github.com/jellyfin/jellyfin-web/pull/7627)
- [Upstream PR #7661](https://github.com/jellyfin/jellyfin-web/pull/7661)
- [Upstream PR #7671](https://github.com/jellyfin/jellyfin-web/pull/7671)
- [Upstream PR #7777](https://github.com/jellyfin/jellyfin-web/pull/7777)
- [Upstream PR #7846](https://github.com/jellyfin/jellyfin-web/pull/7846)
- [Upstream PR #7863](https://github.com/jellyfin/jellyfin-web/pull/7863)
- [Upstream PR #7913](https://github.com/jellyfin/jellyfin-web/pull/7913)
- [Upstream PR #7915](https://github.com/jellyfin/jellyfin-web/pull/7915)

---
---

<p align="center">
<img alt="Logo Banner" src="https://raw.githubusercontent.com/jellyfin/jellyfin-ux/master/branding/SVG/banner-logo-solid.svg?sanitize=true"/>
<br/>
<br/>
<a href="https://github.com/jellyfin/jellyfin-web">
<img alt="GPL 2.0 License" src="https://img.shields.io/github/license/jellyfin/jellyfin-web.svg"/>
</a>
<a href="https://github.com/jellyfin/jellyfin-web/releases">
<img alt="Current Release" src="https://img.shields.io/github/release/jellyfin/jellyfin-web.svg"/>
</a>
<a href="https://translate.jellyfin.org/projects/jellyfin/jellyfin-web/?utm_source=widget">
<img src="https://translate.jellyfin.org/widgets/jellyfin/-/jellyfin-web/svg-badge.svg" alt="Translation Status"/>
</a>
<br/>
<a href="https://opencollective.com/jellyfin">
<img alt="Donate" src="https://img.shields.io/opencollective/all/jellyfin.svg?label=backers"/>
</a>
<a href="https://features.jellyfin.org">
<img alt="Feature Requests" src="https://img.shields.io/badge/fider-vote%20on%20features-success.svg"/>
</a>
<a href="https://matrix.to/#/+jellyfin:matrix.org">
<img alt="Chat on Matrix" src="https://img.shields.io/matrix/jellyfin:matrix.org.svg?logo=matrix"/>
</a>
<a href="https://www.reddit.com/r/jellyfin">
<img alt="Join our Subreddit" src="https://img.shields.io/badge/reddit-r%2Fjellyfin-%23FF5700.svg"/>
</a>
</p>

Jellyfin Web is the frontend used for most of the clients available for end users, such as desktop browsers, Android, and iOS. We welcome all contributions and pull requests! If you have a larger feature in mind please open an issue so we can discuss the implementation before you start. Translations can be improved very easily from our <a href="https://translate.jellyfin.org/projects/jellyfin/jellyfin-web">Weblate</a> instance. Look through the following graphic to see if your native language could use some work!

<a href="https://translate.jellyfin.org/engage/jellyfin/?utm_source=widget">
<img src="https://translate.jellyfin.org/widgets/jellyfin/-/jellyfin-web/multi-auto.svg" alt="Detailed Translation Status"/>
</a>

## Build Process

### Dependencies

- [Node.js](https://nodejs.org/en/download)
- npm (included in Node.js)

### Getting Started

1. Clone or download this repository.

   ```sh
   git clone https://github.com/jellyfin/jellyfin-web.git
   cd jellyfin-web
   ```

2. Install build dependencies in the project directory.

   ```sh
   npm install
   ```

3. Run the web client with webpack for local development.

   ```sh
   npm start
   ```

4. Build the client with sourcemaps available.

   ```sh
   npm run build:development
   ```

Review the [Contributing Guide](./CONTRIBUTING.md) for more information on our process and tech stack.
