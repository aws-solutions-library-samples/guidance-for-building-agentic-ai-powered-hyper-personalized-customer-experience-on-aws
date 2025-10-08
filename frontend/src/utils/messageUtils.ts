/**
 * Strips content between <results> and </results> tags from a message string
 * @param content - The original message content
 * @returns The message content with <results> sections removed
 */
export function stripResultsTags(content: string): string {
  if (!content) return content;
  
  // Use regex to remove everything between <results> and </results> tags (case-insensitive, multiline)
  const resultsTagRegex = /<results\b[^>]*>[\s\S]*?<\/results>/gi;
  
  return content.replace(resultsTagRegex, '').trim();
}

/**
 * Checks if a message contains <results> tags
 * @param content - The message content to check
 * @returns True if the message contains <results> tags
 */
export function hasResultsTags(content: string): boolean {
  if (!content) return false;
  
  const resultsTagRegex = /<results\b[^>]*>/i;
  return resultsTagRegex.test(content);
}

/**
 * Filters streaming content to hide everything after <results> tag until </results>
 * This prevents the JSON content from flashing during streaming
 * @param content - The streaming message content
 * @returns The filtered content that should be displayed during streaming
 */
export function filterStreamingContent(content: string): string {
  if (!content) return content;
  
  // Find the position of <results> tag (case-insensitive)
  const resultsStartRegex = /<results\b[^>]*>/i;
  const resultsStartMatch = content.match(resultsStartRegex);
  
  if (!resultsStartMatch) {
    // No <results> tag found, return full content
    return content;
  }
  
  const resultsStartIndex = resultsStartMatch.index!;
  
  // Check if we have the closing </results> tag
  const beforeResults = content.substring(0, resultsStartIndex);
  const afterResultsStart = content.substring(resultsStartIndex);
  
  const resultsEndRegex = /<\/results>/i;
  const resultsEndMatch = afterResultsStart.match(resultsEndRegex);
  
  if (resultsEndMatch) {
    // We have both opening and closing tags, return content before + content after
    const resultsEndIndex = resultsStartIndex + resultsEndMatch.index! + resultsEndMatch[0].length;
    const afterResults = content.substring(resultsEndIndex);
    return (beforeResults + afterResults).trim();
  } else {
    // We only have opening tag, hide everything after it during streaming
    return beforeResults.trim();
  }
}
