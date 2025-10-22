import { v4 as uuidv4 } from 'uuid';
import fs from 'fs/promises';
import path from 'path';
import { db, storage } from '../config/firebase.js';
import ResumeParser from '../services/resumeParser.js';
import AIAdvisor from '../services/aiAdvisor.js';

const aiAdvisor = new AIAdvisor();

class ResumeController {
  static async uploadResume(req, res, next) {
    try {
      if (!req.file) {
        return res.status(400).json({ success: false, message: 'No file uploaded' });
      }

      const { originalname, path: filePath } = req.file;
      const fileExt = path.extname(originalname).toLowerCase();
      const userId = req.body.userId || 'anonymous';
      const resumeId = uuidv4();

      // Parse the resume
      const parsedResume = await ResumeParser.parseResume(filePath, originalname);

      // Upload to Firebase Storage
      const fileBuffer = await fs.readFile(filePath);
      const fileRef = storage.bucket().file(`resumes/${userId}/${resumeId}${fileExt}`);
      await fileRef.save(fileBuffer, {
        metadata: {
          contentType: req.file.mimetype,
          metadata: {
            originalName: originalname,
            userId: userId
          }
        }
      });

      // Get the public URL
      const [url] = await fileRef.getSignedUrl({
        action: 'read',
        expires: '03-01-2500' // Far future expiration
      });

      // Save to Firestore
      const resumeData = {
        resumeId,
        userId,
        originalName: originalname,
        fileType: fileExt.replace('.', ''),
        fileSize: req.file.size,
        storagePath: `resumes/${userId}/${resumeId}${fileExt}`,
        downloadUrl: url,
        parsedText: parsedResume.text,
        metadata: parsedResume.metadata || {},
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };

      await db.collection('resumes').doc(resumeId).set(resumeData);

      // Clean up the uploaded file
      await fs.unlink(filePath);

      res.status(201).json({
        success: true,
        message: 'Resume uploaded successfully',
        data: {
          resumeId,
          downloadUrl: url
        }
      });
    } catch (error) {
      console.error('Error uploading resume:', error);
      next(error);
    }
  }

  static async analyzeResume(req, res, next) {
    try {
      const { resumeId } = req.params;
      const { jobTitle = 'Software Engineer' } = req.query;

      // Get the resume from Firestore
      const resumeDoc = await db.collection('resumes').doc(resumeId).get();
      
      if (!resumeDoc.exists) {
        return res.status(404).json({ success: false, message: 'Resume not found' });
      }

      const resumeData = resumeDoc.data();
      
      // Analyze the resume with AI
      const analysis = await aiAdvisor.analyzeResume(resumeData.parsedText, jobTitle);

      // Save the analysis
      const analysisId = uuidv4();
      const analysisData = {
        analysisId,
        resumeId,
        userId: resumeData.userId,
        jobTitle,
        analysis,
        createdAt: new Date().toISOString()
      };

      await db.collection('analyses').doc(analysisId).set(analysisData);

      res.status(200).json({
        success: true,
        data: analysis
      });
    } catch (error) {
      console.error('Error analyzing resume:', error);
      next(error);
    }
  }

  static async getUserDashboard(req, res, next) {
    try {
      const { userId } = req.params;
      
      // Get user's resumes
      const resumesSnapshot = await db.collection('resumes')
        .where('userId', '==', userId)
        .orderBy('createdAt', 'desc')
        .get();
      
      const resumes = [];
      for (const doc of resumesSnapshot.docs) {
        const resume = doc.data();
        
        // Get analyses for this resume
        const analysesSnapshot = await db.collection('analyses')
          .where('resumeId', '==', resume.resumeId)
          .orderBy('createdAt', 'desc')
          .get();
        
        const analyses = analysesSnapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        
        resumes.push({
          id: doc.id,
          ...resume,
          analyses
        });
      }

      res.status(200).json({
        success: true,
        data: {
          resumes
        }
      });
    } catch (error) {
      console.error('Error fetching user dashboard:', error);
      next(error);
    }
  }
}

export default ResumeController;
