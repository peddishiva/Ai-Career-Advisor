import { Router } from 'express';

const router = Router();

// AI analysis routes will be added here

// Test endpoint for AI routes
router.get('/test-ai', (req, res) => {
  res.status(200).json({
    success: true,
    message: 'AI routes are working!',
    timestamp: new Date().toISOString()
  });
});

export default router;
