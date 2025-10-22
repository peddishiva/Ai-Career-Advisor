import { Router } from 'express';
import ResumeController from '../controllers/resumeController.js';
import upload from '../utils/fileUpload.js';

const router = Router();

// Upload resume
router.post('/upload', 
  upload.single('resume'),
  ResumeController.uploadResume
);

// Analyze resume
router.get('/analyze/:resumeId', 
  ResumeController.analyzeResume
);

// Get user dashboard
router.get('/user/:userId/dashboard',
  ResumeController.getUserDashboard
);

export default router;
