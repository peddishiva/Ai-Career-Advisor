import fs from 'fs/promises';
import pdf from 'pdf-parse';
import mammoth from 'mammoth';

class ResumeParser {
  static async parseResume(filePath, originalName) {
    try {
      const ext = originalName.split('.').pop().toLowerCase();
      
      if (ext === 'pdf') {
        return await this.parsePDF(filePath);
      } else if (['docx', 'doc'].includes(ext)) {
        return await this.parseDocx(filePath);
      } else {
        throw new Error('Unsupported file format');
      }
    } catch (error) {
      console.error('Error parsing resume:', error);
      throw new Error('Failed to parse resume');
    }
  }

  static async parsePDF(filePath) {
    try {
      const dataBuffer = await fs.readFile(filePath);
      const data = await pdf(dataBuffer);
      return {
        text: data.text,
        metadata: {
          pages: data.numpages,
          info: data.info
        }
      };
    } catch (error) {
      console.error('Error parsing PDF:', error);
      throw new Error('Failed to parse PDF file');
    }
  }

  static async parseDocx(filePath) {
    try {
      const result = await mammoth.extractRawText({ path: filePath });
      return {
        text: result.value,
        metadata: {
          messages: result.messages
        }
      };
    } catch (error) {
      console.error('Error parsing DOCX:', error);
      throw new Error('Failed to parse Word document');
    }
  }
}

export default ResumeParser;
