/**
 * Extracts a product code from a string using a regular expression.
 * @param inputString The string to parse.
 * @returns The extracted product code (e.g., "VIT011") or null if no match is found.
 */
export function extractProductCode(inputString: string): string | null {
  // This regex looks for the literal text "Recommended products: "
  // and then captures one or more alphanumeric characters that follow.
  const regex = /Recommended products: ([A-Za-z0-9]+)/;

  const match = regex.exec(inputString);

  // If a match is found, the captured group is at index 1 of the match array.
  if (match && match[1]) {
    return match[1];
  }

  return null; // Return null if no match was found
}

export function extractAgentResponse(inputString: string): string | null {
  // Use the split method. It's simple and effective for this case.
  const parts = inputString.split('Agent response: ');

  // If the split results in more than one part, the response is the second part.
  if (parts.length > 1) {
    return parts[1].trim(); // .trim() removes any leading/trailing whitespace
  }

  return null;
}

// You can add other related utility functions to this file as well.