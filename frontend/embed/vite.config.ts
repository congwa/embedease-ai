import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// 自定义插件：将 CSS 内联到 JS 中
function cssInjectedByJsPlugin(): Plugin {
  return {
    name: "css-injected-by-js",
    apply: "build",
    enforce: "post",
    generateBundle(_, bundle) {
      let cssCode = "";
      const cssFileNames: string[] = [];

      // 收集所有 CSS
      for (const [fileName, chunk] of Object.entries(bundle)) {
        if (fileName.endsWith(".css") && chunk.type === "asset") {
          cssCode += chunk.source;
          cssFileNames.push(fileName);
        }
      }

      // 删除 CSS 文件
      for (const fileName of cssFileNames) {
        delete bundle[fileName];
      }

      // 将 CSS 注入到 JS 中
      if (cssCode) {
        for (const chunk of Object.values(bundle)) {
          if (chunk.type === "chunk" && chunk.isEntry) {
            const injectCode = `
(function(){
  var style = document.createElement('style');
  style.textContent = ${JSON.stringify(cssCode)};
  document.head.appendChild(style);
})();
`;
            chunk.code = injectCode + chunk.code;
          }
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), cssInjectedByJsPlugin()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: resolve(__dirname, "entry.tsx"),
      name: "EmbedAiChat",
      fileName: () => "embed-ai-chat.js",
      formats: ["iife"],
    },
    rollupOptions: {
      output: {
        // 确保所有代码打包到一个文件
        inlineDynamicImports: true,
        // 不生成额外的 chunk
        manualChunks: undefined,
      },
    },
    // 输出到 dist/embed 目录
    outDir: resolve(__dirname, "../dist/embed"),
    // 清空输出目录
    emptyOutDir: true,
    // 不复制 public 目录
    copyPublicDir: false,
    // 内联所有资源
    assetsInlineLimit: 100000,
    // CSS 代码分割关闭，内联到 JS
    cssCodeSplit: false,
    // 生成 sourcemap 便于调试
    sourcemap: false,
    // 压缩
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: false,
        drop_debugger: true,
      },
    },
  },
  // CSS 配置
  css: {
    // 将 CSS 注入到 JS 中
    postcss: {},
  },
});
