import pdf from 'pdf-parse';
import mammoth from 'mammoth';

// Extract text from PDF buffer
async function extractTextFromPdf(buffer) {
  try {
    const data = await pdf(buffer);
    return data.text;
  } catch (error) {
    console.error('Error extracting text from PDF:', error);
    throw new Error('Failed to process PDF file');
  }
}

// Extract text from DOCX buffer
async function extractTextFromDocx(buffer) {
  try {
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  } catch (error) {
    console.error('Error extracting text from DOCX:', error);
    throw new Error('Failed to process DOCX file');
  }
}

// Analyze resume text using AI (placeholder - integrate with your AI service)
async function analyzeWithAI(text) {
  // This is a mock implementation
  // In a real app, you would call your AI service here
  return new Promise((resolve) => {
    // Simulate AI processing delay
    setTimeout(() => {
      // Mock analysis results
      resolve({
        skills: [
          { name: 'JavaScript', category: 'Programming', level: 'Advanced' },
          { name: 'React', category: 'Frontend', level: 'Advanced' },
          { name: 'Node.js', category: 'Backend', level: 'Intermediate' },
        ],
        missingSkills: [
          { name: 'TypeScript', reason: 'Required for modern frontend development' },
          { name: 'Docker', reason: 'Industry standard for containerization' },
        ],
        recommendations: [
          {
            skill: 'TypeScript',
            resources: [
              { name: 'TypeScript Handbook', url: 'https://www.typescriptlang.org/docs/handbook/' },
              { name: 'TypeScript in 5 minutes', type: 'tutorial', url: 'https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html' },
            ]
          },
          {
            skill: 'Docker',
            resources: [
              { name: 'Docker Getting Started', url: 'https://docs.docker.com/get-started/' },
              { name: 'Docker for Node.js', type: 'tutorial', url: 'https://nodejs.org/en/docs/guides/nodejs-docker-webapp/' },
            ]
          }
        ],
        score: 75,
        summary: 'Strong frontend skills with React, but could benefit from learning TypeScript and containerization with Docker.'
      });
    }, 1000);
  });
}

// Main function to analyze resume
export async function analyzeResume(buffer, fileName) {
  try {
    // Determine file type and extract text
    let text;
    if (fileName.endsWith('.pdf')) {
      text = await extractTextFromPdf(buffer);
    } else if (fileName.endsWith('.docx')) {
      text = await extractTextFromDocx(buffer);
    } else {
      throw new Error('Unsupported file type. Please upload a PDF or DOCX file.');
    }

    // Analyze text with AI
    const analysis = await analyzeWithAI(text);
    
    return {
      ...analysis,
      textPreview: text.substring(0, 500) + (text.length > 500 ? '...' : '')
    };
    
  } catch (error) {
    console.error('Error in analyzeResume:', error);
    throw error;
  }
}
