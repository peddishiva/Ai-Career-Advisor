import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { initializeFirebase } from './config/firebase.js';
import resumeRoutes from './routes/resumeRoutes.js';
import aiRoutes from './routes/aiRoutes.js';
import testRoutes from './routes/testRoutes.js';
import uploadRoutes from './routes/uploadRoutes.js';

// Load environment variables
dotenv.config();

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
  origin: 'http://localhost:3000',
  optionsSuccessStatus: 200
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize Firebase
await initializeFirebase();

// API Routes
app.use('/api', resumeRoutes);
app.use('/api', aiRoutes);
app.use('/api', testRoutes);
app.use('/api', uploadRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'AI Career Advisor API is running' });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    message: 'Internal Server Error',
    error: process.env.NODE_ENV === 'development' ? err.message : {}
  });
});

// Start server with port handling
const startServer = async () => {
  const server = app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  }).on('error', async (err) => {
    if (err.code === 'EADDRINUSE') {
      console.log(`Port ${PORT} is in use, trying port ${Number(PORT) + 1}...`);
      // Try the next port
      const nextPort = Number(PORT) + 1;
      app.listen(nextPort, () => {
        console.log(`Server running on port ${nextPort} (${PORT} was in use)`);
        console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
      });
    } else {
      console.error('Error starting server:', err);
      process.exit(1);
    }
  });

  // Handle process termination
  process.on('SIGTERM', () => {
    console.log('SIGTERM received. Shutting down gracefully');
    server.close(() => {
      console.log('Process terminated');
    });
  });
};

startServer();

export default app;
