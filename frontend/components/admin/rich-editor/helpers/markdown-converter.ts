import { marked } from "marked";

/**
 * Convert Markdown to HTML
 */
export function markdownToHtml(markdown: string): string {
  if (!markdown) return "";
  try {
    return marked.parse(markdown, { async: false }) as string;
  } catch (error) {
    console.error("Error converting markdown to HTML:", error);
    return markdown;
  }
}

/**
 * Convert HTML to Markdown (simple implementation)
 */
export function htmlToMarkdown(html: string): string {
  if (!html) return "";
  
  // Simple HTML to Markdown conversion
  let markdown = html;
  
  // Convert headings
  markdown = markdown.replace(/<h1[^>]*>(.*?)<\/h1>/gi, "# $1\n\n");
  markdown = markdown.replace(/<h2[^>]*>(.*?)<\/h2>/gi, "## $1\n\n");
  markdown = markdown.replace(/<h3[^>]*>(.*?)<\/h3>/gi, "### $1\n\n");
  markdown = markdown.replace(/<h4[^>]*>(.*?)<\/h4>/gi, "#### $1\n\n");
  markdown = markdown.replace(/<h5[^>]*>(.*?)<\/h5>/gi, "##### $1\n\n");
  markdown = markdown.replace(/<h6[^>]*>(.*?)<\/h6>/gi, "###### $1\n\n");
  
  // Convert bold and italic
  markdown = markdown.replace(/<strong[^>]*>(.*?)<\/strong>/gi, "**$1**");
  markdown = markdown.replace(/<b[^>]*>(.*?)<\/b>/gi, "**$1**");
  markdown = markdown.replace(/<em[^>]*>(.*?)<\/em>/gi, "*$1*");
  markdown = markdown.replace(/<i[^>]*>(.*?)<\/i>/gi, "*$1*");
  
  // Convert links
  markdown = markdown.replace(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/gi, "[$2]($1)");
  
  // Convert images
  markdown = markdown.replace(/<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*\/?>/gi, "![$2]($1)");
  markdown = markdown.replace(/<img[^>]*src="([^"]*)"[^>]*\/?>/gi, "![]($1)");
  
  // Convert lists
  markdown = markdown.replace(/<ul[^>]*>/gi, "");
  markdown = markdown.replace(/<\/ul>/gi, "\n");
  markdown = markdown.replace(/<ol[^>]*>/gi, "");
  markdown = markdown.replace(/<\/ol>/gi, "\n");
  markdown = markdown.replace(/<li[^>]*>(.*?)<\/li>/gi, "- $1\n");
  
  // Convert code
  markdown = markdown.replace(/<code[^>]*>(.*?)<\/code>/gi, "`$1`");
  markdown = markdown.replace(/<pre[^>]*><code[^>]*>(.*?)<\/code><\/pre>/gis, "```\n$1\n```\n\n");
  
  // Convert blockquote
  markdown = markdown.replace(/<blockquote[^>]*>(.*?)<\/blockquote>/gis, (_, content) => {
    return content.split("\n").map((line: string) => `> ${line}`).join("\n") + "\n\n";
  });
  
  // Convert paragraphs and line breaks
  markdown = markdown.replace(/<p[^>]*>(.*?)<\/p>/gi, "$1\n\n");
  markdown = markdown.replace(/<br\s*\/?>/gi, "\n");
  
  // Remove remaining HTML tags
  markdown = markdown.replace(/<[^>]+>/g, "");
  
  // Decode HTML entities
  markdown = markdown.replace(/&nbsp;/g, " ");
  markdown = markdown.replace(/&lt;/g, "<");
  markdown = markdown.replace(/&gt;/g, ">");
  markdown = markdown.replace(/&amp;/g, "&");
  markdown = markdown.replace(/&quot;/g, '"');
  
  // Clean up extra whitespace
  markdown = markdown.replace(/\n{3,}/g, "\n\n");
  markdown = markdown.trim();
  
  return markdown;
}

/**
 * Check if content appears to be Markdown
 */
export function isMarkdownContent(content: string): boolean {
  if (!content) return false;
  
  // Check for common Markdown patterns
  const markdownPatterns = [
    /^#{1,6}\s/m,           // Headings
    /\*\*[^*]+\*\*/,        // Bold
    /\*[^*]+\*/,            // Italic
    /\[([^\]]+)\]\([^)]+\)/, // Links
    /!\[([^\]]*)\]\([^)]+\)/, // Images
    /^[-*+]\s/m,            // Unordered lists
    /^\d+\.\s/m,            // Ordered lists
    /^>\s/m,                // Blockquotes
    /`[^`]+`/,              // Inline code
    /^```/m,                // Code blocks
  ];
  
  return markdownPatterns.some((pattern) => pattern.test(content));
}

/**
 * Get preview text from Markdown content
 */
export function markdownToPreviewText(markdown: string, maxLength = 50): string {
  if (!markdown) return "";
  
  // Remove Markdown formatting
  let text = markdown;
  
  // Remove code blocks
  text = text.replace(/```[\s\S]*?```/g, "");
  text = text.replace(/`[^`]+`/g, "");
  
  // Remove headings markers
  text = text.replace(/^#{1,6}\s+/gm, "");
  
  // Remove bold/italic markers
  text = text.replace(/\*\*([^*]+)\*\*/g, "$1");
  text = text.replace(/\*([^*]+)\*/g, "$1");
  text = text.replace(/__([^_]+)__/g, "$1");
  text = text.replace(/_([^_]+)_/g, "$1");
  
  // Remove links, keep text
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
  
  // Remove images
  text = text.replace(/!\[([^\]]*)\]\([^)]+\)/g, "");
  
  // Remove blockquote markers
  text = text.replace(/^>\s+/gm, "");
  
  // Remove list markers
  text = text.replace(/^[-*+]\s+/gm, "");
  text = text.replace(/^\d+\.\s+/gm, "");
  
  // Clean up whitespace
  text = text.replace(/\n+/g, " ");
  text = text.replace(/\s+/g, " ");
  text = text.trim();
  
  // Truncate
  if (text.length > maxLength) {
    text = text.substring(0, maxLength) + "...";
  }
  
  return text;
}
