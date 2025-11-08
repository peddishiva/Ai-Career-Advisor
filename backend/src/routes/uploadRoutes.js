import express from 'express';
import multer from 'multer';
import { analyzeResume } from '../services/resumeAnalysisService.js';
import { saveAnalysis } from '../services/firestoreService.js';
import { v4 as uuidv4 } from 'uuid';

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// Upload and analyze resume
router.post('/upload', upload.single('resume'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, message: 'No file uploaded' });
    }

    // For demo, using a mock user ID - in production, get from auth
    const userId = req.user?.uid || 'demo-user';
    const analysisId = uuidv4();
    
    // Process the file
    const result = await analyzeResume(req.file.buffer, req.file.originalname);
    
    // Save to Firestore
    await saveAnalysis(userId, analysisId, {
      ...result,
      fileName: req.file.originalname,
      uploadDate: new Date().toISOString(),
    });

    res.status(200).json({
      success: true,
      analysisId,
      ...result
    });

  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({
      success: false,
      message: 'Error processing resume',
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// Get user's analysis
router.get('/analysis/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    // In a real app, verify the user has access to this data
    const analysis = await getLatestAnalysis(userId);
    
    if (!analysis) {
      return res.status(404).json({
        success: false,
        message: 'No analysis found for this user'
      });
    }

    res.status(200).json({
      success: true,
      data: analysis
    });

  } catch (error) {
    console.error('Analysis fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Error fetching analysis'
    });
  }
});

export default router;
