/**
 * 自动截屏脚本
 * 使用 Playwright 对主要功能页面进行全屏截屏
 * 
 * 使用方法：
 * 1. 确保前后端服务已启动
 * 2. 运行：npx tsx .windsurf/skills/auto-screenshot/scripts/screenshot.ts
 */

import { chromium, Browser, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

// 截屏配置
const CONFIG = {
  baseUrl: 'http://localhost:3000',
  outputDir: './docs/screenshots',
  viewport: { width: 1920, height: 1080 },
  timeout: 30000,
};

// 主要功能页面列表
const PAGES = [
  // 首页
  { path: '/', name: 'landing-page', description: '产品落地页' },
  
  // 聊天界面
  { path: '/chat', name: 'chat-interface', description: '用户聊天界面' },
  
  // 管理后台
  { path: '/admin', name: 'admin-dashboard', description: '管理后台仪表盘' },
  { path: '/admin/quick-setup', name: 'quick-setup', description: '快速配置向导' },
  { path: '/admin/agents', name: 'agent-list', description: 'Agent 列表' },
  { path: '/admin/single', name: 'single-mode', description: '单 Agent 模式配置' },
  { path: '/admin/multi', name: 'multi-mode', description: '编排模式配置' },
  
  // 系统设置
  { path: '/admin/settings', name: 'settings', description: '系统设置' },
  { path: '/admin/settings/mode', name: 'mode-settings', description: '模式设置' },
  
  // 技能管理
  { path: '/admin/skills', name: 'skills-list', description: '技能列表' },
  
  // 客服工作台
  { path: '/support', name: 'support-workbench', description: '客服工作台' },
];

async function ensureOutputDir() {
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  }
}

async function waitForPageLoad(page: Page) {
  // 等待页面加载完成
  await page.waitForLoadState('networkidle', { timeout: CONFIG.timeout });
  // 额外等待动画完成
  await page.waitForTimeout(1000);
}

async function takeScreenshot(page: Page, pageConfig: typeof PAGES[0]) {
  const { path: pagePath, name, description } = pageConfig;
  const url = `${CONFIG.baseUrl}${pagePath}`;
  
  console.log(`📸 截屏: ${description} (${pagePath})`);
  
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: CONFIG.timeout });
    await waitForPageLoad(page);
    
    const filename = `${name}.png`;
    const filepath = path.join(CONFIG.outputDir, filename);
    
    await page.screenshot({
      path: filepath,
      fullPage: false, // 只截取视口
    });
    
    console.log(`   ✅ 已保存: ${filepath}`);
    return { success: true, path: filepath };
  } catch (error) {
    console.log(`   ❌ 失败: ${error instanceof Error ? error.message : error}`);
    return { success: false, error };
  }
}

async function main() {
  console.log('🚀 开始自动截屏流程...\n');
  console.log(`📁 输出目录: ${CONFIG.outputDir}`);
  console.log(`🖥️  视口大小: ${CONFIG.viewport.width}x${CONFIG.viewport.height}`);
  console.log(`🌐 基础 URL: ${CONFIG.baseUrl}\n`);
  
  ensureOutputDir();
  
  let browser: Browser | null = null;
  
  try {
    // 启动浏览器
    browser = await chromium.launch({
      headless: true,
    });
    
    const context = await browser.newContext({
      viewport: CONFIG.viewport,
      deviceScaleFactor: 2, // 高清截图
    });
    
    const page = await context.newPage();
    
    // 检查服务是否可用
    console.log('🔍 检查服务是否可用...');
    try {
      await page.goto(CONFIG.baseUrl, { timeout: 10000 });
      console.log('   ✅ 服务可用\n');
    } catch {
      console.log('   ❌ 服务不可用，请先启动前端服务\n');
      console.log('   运行: cd frontend && pnpm dev');
      process.exit(1);
    }
    
    // 截屏所有页面
    const results: { page: string; success: boolean }[] = [];
    
    for (const pageConfig of PAGES) {
      const result = await takeScreenshot(page, pageConfig);
      results.push({ page: pageConfig.name, success: result.success });
    }
    
    // 输出统计
    console.log('\n📊 截屏统计:');
    const successCount = results.filter(r => r.success).length;
    console.log(`   成功: ${successCount}/${results.length}`);
    
    if (successCount < results.length) {
      console.log('   失败的页面:');
      results.filter(r => !r.success).forEach(r => {
        console.log(`     - ${r.page}`);
      });
    }
    
    // 生成索引文件
    const indexContent = `# 页面截屏

生成时间: ${new Date().toLocaleString('zh-CN')}

| 页面 | 描述 | 截图 |
|------|------|------|
${PAGES.map(p => `| ${p.path} | ${p.description} | ![${p.name}](screenshots/${p.name}.png) |`).join('\n')}
`;
    
    fs.writeFileSync(path.join('./docs', 'SCREENSHOTS.md'), indexContent);
    console.log('\n📝 已生成索引文件: docs/SCREENSHOTS.md');
    
  } catch (error) {
    console.error('❌ 截屏过程出错:', error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
  
  console.log('\n✅ 截屏完成!');
}

main();
