"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { AnimatedGradientText } from "@/components/ui/animated-gradient-text";
import { PulseButton } from "@/components/ui/pulse-button";
import {
  ArrowRight,
  MessageSquare,
  Zap,
  Settings,
  BarChart3,
  Users,
  Bot,
  Globe,
  Smartphone,
  Sparkles,
  Brain,
  ShoppingCart,
  HelpCircle,
  BookOpen,
  Wrench,
  ChevronRight,
  Check,
  Bell,
  Link2,
  MessageCircle,
  Activity,
} from "lucide-react";

const fadeInUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6 },
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-primary/20">
      {/* Navigation */}
      <nav className="fixed top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <motion.div
              className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white font-bold shadow-lg shadow-violet-500/25"
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={{ type: "spring", stiffness: 400 }}
            >
              E
            </motion.div>
            <span className="font-bold text-xl tracking-tight">EmbedeaseAi</span>
          </div>

          <div className="flex items-center gap-4">
            <Link href="/chat" className="text-sm text-muted-foreground hover:text-foreground transition-colors hidden sm:block">
              演示对话
            </Link>
            <PulseButton href="/admin">
              进入后台体验 <ArrowRight className="w-4 h-4" />
            </PulseButton>
          </div>
        </div>
      </nav>

      <main>
        {/* Hero Section with Aurora Background */}
        <AuroraBackground className="pt-32 pb-20 lg:pt-40 lg:pb-32">
          <div className="container mx-auto px-4 text-center relative z-10">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="max-w-5xl mx-auto space-y-8"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
              >
                <Badge
                  variant="secondary"
                  className="px-4 py-2 rounded-full text-primary bg-primary/10 border-primary/20 text-sm"
                >
                  🚀 让每一个访客都成为潜在客户
                </Badge>
              </motion.div>

              <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight leading-tight">
                <motion.span
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="block"
                >
                  匿名用户提问
                </motion.span>
                <motion.span
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="block"
                >
                  <AnimatedGradientText>企业微信实时推送</AnimatedGradientText>
                </motion.span>
                <motion.span
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                  className="block text-3xl md:text-4xl lg:text-5xl mt-4 text-muted-foreground font-medium"
                >
                  点击链接，直连客户
                </motion.span>
              </h1>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.9 }}
                className="text-lg md:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed"
              >
                EmbedeaseAi 不仅仅是智能客服，它能将网站的匿名咨询
                <span className="text-foreground font-semibold">实时推送到企业微信</span>
                ，让您一键直连客户，抓住稍纵即逝的商机。
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.1 }}
                className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4"
              >
                <Link href="/admin">
                  <Button
                    size="lg"
                    className="h-14 px-10 text-lg rounded-full shadow-xl shadow-primary/20 hover:shadow-primary/40 transition-all"
                  >
                    立即免费体验 <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
                <Link href="/chat">
                  <Button
                    variant="outline"
                    size="lg"
                    className="h-14 px-10 text-lg rounded-full border-2"
                  >
                    体验 AI 对话
                  </Button>
                </Link>
              </motion.div>
            </motion.div>
          </div>
        </AuroraBackground>

        {/* Conversion Flow Section - Core Highlight */}
        <section className="py-24 bg-muted/30 relative overflow-hidden">
          <div className="absolute inset-0 bg-grid-pattern opacity-5" />
          <div className="container mx-auto px-4 relative z-10">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <Badge variant="outline" className="mb-4">核心优势</Badge>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                颠覆传统的<AnimatedGradientText>转化模式</AnimatedGradientText>
              </h2>
              <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
                从匿名访问到建立联系，只需一步。传统客服等待用户上线，我们主动触达每一个商机。
              </p>
            </motion.div>

            {/* Conversion Flow Cards */}
            <div className="relative max-w-5xl mx-auto">
              {/* Connection Line */}
              <div className="absolute top-1/2 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 hidden md:block -translate-y-1/2 rounded-full opacity-30" />

              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative z-10">
                {[
                  {
                    icon: Users,
                    title: "匿名用户提问",
                    desc: "用户在网站悬浮窗输入需求",
                    color: "from-blue-500 to-blue-600",
                    step: "01",
                  },
                  {
                    icon: Bot,
                    title: "AI 智能响应",
                    desc: "AI 立即回答，留住用户",
                    color: "from-violet-500 to-violet-600",
                    step: "02",
                  },
                  {
                    icon: Bell,
                    title: "企业微信推送",
                    desc: "包含需求摘要和对话链接",
                    color: "from-pink-500 to-pink-600",
                    step: "03",
                  },
                  {
                    icon: MessageCircle,
                    title: "一键直连对话",
                    desc: "点击链接直接接管会话",
                    color: "from-orange-500 to-orange-600",
                    step: "04",
                  },
                ].map((step, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.15 }}
                  >
                    <Card className="h-full border-none shadow-xl hover:shadow-2xl transition-all hover:-translate-y-2 bg-background/80 backdrop-blur group">
                      <CardContent className="pt-8 text-center space-y-4">
                        <div className="text-xs font-bold text-muted-foreground mb-2">
                          STEP {step.step}
                        </div>
                        <motion.div
                          className={`w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br ${step.color} shadow-lg flex items-center justify-center text-white`}
                          whileHover={{ scale: 1.1, rotate: 5 }}
                        >
                          <step.icon className="w-8 h-8" />
                        </motion.div>
                        <h3 className="text-lg font-bold">{step.title}</h3>
                        <p className="text-sm text-muted-foreground">{step.desc}</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl mx-auto"
            >
              {[
                { value: "80%", label: "响应速度提升", desc: "从 5 分钟降至 1 分钟" },
                { value: "35%", label: "转化率提升", desc: "及时介入高意向客户" },
                { value: "50%", label: "满意度提升", desc: "AI + 人工双重保障" },
              ].map((stat, i) => (
                <div key={i} className="text-center">
                  <div className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
                    {stat.value}
                  </div>
                  <div className="font-semibold mt-1">{stat.label}</div>
                  <div className="text-sm text-muted-foreground">{stat.desc}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* Four Agent Types */}
        <section className="py-24">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <Badge variant="outline" className="mb-4">Agent 类型</Badge>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                四种专业 Agent，覆盖所有场景
              </h2>
              <p className="text-muted-foreground text-lg">按需选择，即开即用</p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  icon: ShoppingCart,
                  title: "商品推荐助手",
                  desc: "智能搜索、预算筛选、商品对比、精准推荐",
                  color: "from-orange-500 to-red-500",
                  features: ["智能搜索", "预算筛选", "商品对比"],
                },
                {
                  icon: HelpCircle,
                  title: "FAQ 问答助手",
                  desc: "快速匹配 FAQ、多轮澄清、人工转接",
                  color: "from-blue-500 to-cyan-500",
                  features: ["精准匹配", "多轮澄清", "自动转接"],
                },
                {
                  icon: BookOpen,
                  title: "知识库助手",
                  desc: "语义搜索、文档检索、来源引用",
                  color: "from-green-500 to-emerald-500",
                  features: ["语义搜索", "文档检索", "来源引用"],
                },
                {
                  icon: Wrench,
                  title: "自定义助手",
                  desc: "自由配置工具、中间件、知识源",
                  color: "from-violet-500 to-purple-500",
                  features: ["完全自定义", "混合能力", "灵活配置"],
                },
              ].map((agent, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                >
                  <Card className="h-full hover:shadow-xl transition-all hover:-translate-y-1 group overflow-hidden">
                    <CardHeader className="pb-2">
                      <motion.div
                        className={`w-14 h-14 rounded-xl bg-gradient-to-br ${agent.color} flex items-center justify-center text-white shadow-lg mb-4`}
                        whileHover={{ scale: 1.1 }}
                      >
                        <agent.icon className="w-7 h-7" />
                      </motion.div>
                      <CardTitle className="text-xl">{agent.title}</CardTitle>
                      <CardDescription>{agent.desc}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {agent.features.map((f, j) => (
                          <Badge key={j} variant="secondary" className="text-xs">
                            {f}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Three Dialog Modes */}
        <section className="py-24 bg-muted/30">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <Badge variant="outline" className="mb-4">对话模式</Badge>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                三种模式，精准控制回答策略
              </h2>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {[
                {
                  mode: "Natural",
                  title: "自然对话模式",
                  desc: "平衡体验和准确性，优先使用工具查询，信息不足时主动追问",
                  color: "bg-green-500",
                  icon: "🟢",
                  example: '"帮我找耳机" → 追问预算和用途后推荐',
                },
                {
                  mode: "Free",
                  title: "自由聊天模式",
                  desc: "可以闲聊任何话题，不强制回到业务，像通用助手一样",
                  color: "bg-blue-500",
                  icon: "🔵",
                  example: '"今天天气真好" → 友好回应并适时引导',
                },
                {
                  mode: "Strict",
                  title: "严格模式",
                  desc: "必须基于工具查询结果回答，杜绝猜测和编造，适合高价值场景",
                  color: "bg-red-500",
                  icon: "🔴",
                  example: '"支持5G吗？" → 查询后给出准确参数',
                },
              ].map((mode, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15 }}
                >
                  <Card className="h-full hover:shadow-xl transition-all">
                    <CardHeader>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-2xl">{mode.icon}</span>
                        <Badge variant="outline">{mode.mode}</Badge>
                      </div>
                      <CardTitle>{mode.title}</CardTitle>
                      <CardDescription>{mode.desc}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="bg-muted rounded-lg p-3 text-sm">
                        <span className="text-muted-foreground">示例：</span>
                        <span className="ml-1">{mode.example}</span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Smart Memory System */}
        <section className="py-24">
          <div className="container mx-auto px-4">
            <div className="flex flex-col lg:flex-row items-center gap-16">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className="lg:w-1/2 space-y-6"
              >
                <Badge variant="outline">智能记忆</Badge>
                <h2 className="text-3xl md:text-4xl font-bold">
                  记住每一个客户的偏好
                </h2>
                <p className="text-lg text-muted-foreground">
                  三层记忆系统，让 AI 真正理解用户，提供个性化推荐体验。
                </p>
                <div className="space-y-4">
                  {[
                    {
                      icon: Users,
                      title: "用户画像",
                      desc: "记住偏好和习惯，如「喜欢苹果品牌」「预算 3000 左右」",
                    },
                    {
                      icon: Brain,
                      title: "事实记忆",
                      desc: "存储关键事实，如「上次看过索尼 XM5」",
                    },
                    {
                      icon: Activity,
                      title: "知识图谱",
                      desc: "建立实体关联，如「用户 → 喜欢 → 降噪耳机」",
                    },
                  ].map((item, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.1 }}
                      className="flex gap-4 items-start"
                    >
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <item.icon className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-semibold">{item.title}</h4>
                        <p className="text-sm text-muted-foreground">{item.desc}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className="lg:w-1/2"
              >
                <Card className="border-none shadow-2xl bg-gradient-to-br from-violet-500/10 to-pink-500/10">
                  <CardContent className="p-8">
                    <div className="space-y-4 font-mono text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-green-500">●</span>
                        <span className="text-muted-foreground">用户偏好已加载</span>
                      </div>
                      <div className="bg-background/50 rounded-lg p-4 space-y-2">
                        <div className="text-xs text-muted-foreground">用户画像</div>
                        <div className="text-sm">品牌偏好: <span className="text-primary">Apple, Sony</span></div>
                        <div className="text-sm">预算范围: <span className="text-primary">2000-4000</span></div>
                        <div className="text-sm">使用场景: <span className="text-primary">通勤, 运动</span></div>
                      </div>
                      <div className="text-blue-500">→ 基于历史推荐 AirPods Pro 2</div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Quick Setup */}
        <section className="py-24 bg-primary/5 border-y">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <Badge variant="outline" className="mb-4">快速配置</Badge>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                3 分钟完成配置，零代码上线
              </h2>
              <p className="text-muted-foreground text-lg">
                可视化向导，3 步即可创建专属 AI 助手
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {[
                {
                  step: "01",
                  title: "选择 Agent 类型",
                  desc: "商品推荐 / FAQ 问答 / 知识库 / 自定义",
                },
                {
                  step: "02",
                  title: "配置知识源",
                  desc: "导入商品、添加 FAQ、上传文档",
                },
                {
                  step: "03",
                  title: "设置开场白",
                  desc: "配置欢迎语、推荐问题、渠道策略",
                },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15 }}
                  className="text-center"
                >
                  <div className="w-16 h-16 mx-auto rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold mb-4">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                  <p className="text-muted-foreground">{item.desc}</p>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="mt-12 text-center"
            >
              <Link href="/admin/quick-setup">
                <Button size="lg" className="h-12 px-8">
                  开始配置 <ChevronRight className="ml-1 w-5 h-5" />
                </Button>
              </Link>
            </motion.div>
          </div>
        </section>

        {/* More Features */}
        <section className="py-24">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <Badge variant="outline" className="mb-4">更多能力</Badge>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                丰富的工具生态，开箱即用
              </h2>
            </motion.div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
              {[
                { icon: Globe, title: "一键嵌入" },
                { icon: Zap, title: "多 LLM 支持" },
                { icon: BarChart3, title: "数据分析" },
                { icon: Settings, title: "后台管理" },
                { icon: Smartphone, title: "移动友好" },
                { icon: Link2, title: "Webhook 推送" },
                { icon: MessageSquare, title: "人工转接" },
                { icon: Sparkles, title: "流式输出" },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card className="text-center hover:shadow-lg transition-all hover:-translate-y-1">
                    <CardContent className="pt-6">
                      <item.icon className="w-8 h-8 mx-auto text-primary mb-3" />
                      <div className="font-medium text-sm">{item.title}</div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-24 bg-gradient-to-br from-blue-600 via-violet-600 to-pink-600 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
          <motion.div
            className="absolute inset-0"
            animate={{
              background: [
                "radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%)",
                "radial-gradient(circle at 80% 50%, rgba(255,255,255,0.1) 0%, transparent 50%)",
                "radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%)",
              ],
            }}
            transition={{ duration: 10, repeat: Infinity }}
          />
          <div className="container mx-auto px-4 text-center relative z-10">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="max-w-3xl mx-auto space-y-8"
            >
              <h2 className="text-3xl md:text-5xl font-bold">
                准备好提升转化率了吗？
              </h2>
              <p className="text-xl text-white/80">
                无需犹豫，立即开始构建您的 AI 销售助手。
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link href="/admin">
                  <Button
                    size="lg"
                    variant="secondary"
                    className="h-14 px-10 text-lg rounded-full"
                  >
                    进入管理后台 <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
                <Link href="https://github.com/congwa/embedeaseai-agent" target="_blank">
                  <Button
                    size="lg"
                    variant="outline"
                    className="h-14 px-10 text-lg rounded-full border-white/30 text-white hover:bg-white/10"
                  >
                    查看 GitHub
                  </Button>
                </Link>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-12 bg-muted/20">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white font-bold">
                E
              </div>
              <span className="font-bold">EmbedEase AI</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2026 EmbedEase AI. 让每一个匿名访客都成为潜在客户。
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
