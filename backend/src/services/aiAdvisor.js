class AIAdvisor {
  constructor(apiKey) {
    this.apiKey = apiKey || process.env.GEMINI_API_KEY;
    this.apiUrl = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';
  }

  async analyzeResume(resumeText, jobTitle = 'Software Engineer') {
    try {
      const prompt = `You are an AI Career Advisor. Analyze the following resume text and provide detailed feedback.

Resume:
${resumeText.substring(0, 28000)}  // Gemini has a token limit

Please analyze this resume for a ${jobTitle} role and provide a structured JSON response with these fields:
1. skills: { technical: string[], soft: string[] } - List of identified technical and soft skills
2. missingSkills: string[] - Key skills missing for the target role
3. recommendations: Array<{ type: string, title: string, platform: string, url: string }> - Learning resources
4. careerAdvice: string - Brief personalized career advice

Format your response as a valid JSON object.`;

      const response = await this.callGeminiAPI(prompt);
      return this.parseAIResponse(response);
    } catch (error) {
      console.error('Error in AI analysis:', error);
      throw new Error('Failed to analyze resume with AI: ' + error.message);
    }
  }

  async callGeminiAPI(prompt) {
    const url = `${this.apiUrl}?key=${this.apiKey}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: prompt
            }]
          }],
          generationConfig: {
            temperature: 0.7,
            topK: 40,
            topP: 0.95,
            maxOutputTokens: 2048,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`Gemini API error: ${errorData.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return data.candidates?.[0]?.content?.parts?.[0]?.text || '';
    } catch (error) {
      console.error('Error calling Gemini API:', error);
      throw error;
    }
  }

  parseAIResponse(response) {
    try {
      // Extract JSON from markdown code block if present
      let jsonStr = response;
      const jsonMatch = response.match(/```(?:json)?\n([\s\S]*?)\n```/);
      if (jsonMatch && jsonMatch[1]) {
        jsonStr = jsonMatch[1];
      }

      const result = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
      
      // Validate the response structure
      if (!result.skills || !result.recommendations) {
        throw new Error('Invalid response format from AI service');
      }
      
      return result;
    } catch (error) {
      console.error('Error parsing AI response:', error);
      throw new Error('Failed to parse AI response. The response format was invalid.');
    }
  }
}

export default AIAdvisor;
