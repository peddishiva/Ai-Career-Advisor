import { Router } from 'express';

const router = Router();

// Test endpoint for connectivity check
router.get('/test-connection', (req, res) => {
  res.status(200).json({
    success: true,
    message: 'Backend is connected successfully!',
    timestamp: new Date().toISOString()
  });
});

export default router;
