import { db } from '../config/firebase.js';
import { collection, addDoc, getDocs, query, where, orderBy, limit } from 'firebase/firestore';

const ANALYSES_COLLECTION = 'resume_analyses';

/**
 * Save analysis results to Firestore
 * @param {string} userId - User ID
 * @param {string} analysisId - Unique analysis ID
 * @param {object} data - Analysis data to save
 * @returns {Promise<string>} Document ID
 */
export async function saveAnalysis(userId, analysisId, data) {
  try {
    const docRef = await addDoc(collection(db, ANALYSES_COLLECTION), {
      userId,
      analysisId,
      ...data,
      createdAt: new Date().toISOString(),
    });
    return docRef.id;
  } catch (error) {
    console.error('Error saving analysis:', error);
    throw new Error('Failed to save analysis');
  }
}

/**
 * Get the latest analysis for a user
 * @param {string} userId - User ID
 * @returns {Promise<object|null>} Latest analysis or null if not found
 */
export async function getLatestAnalysis(userId) {
  try {
    const q = query(
      collection(db, ANALYSES_COLLECTION),
      where('userId', '==', userId),
      orderBy('createdAt', 'desc'),
      limit(1)
    );

    const querySnapshot = await getDocs(q);
    
    if (querySnapshot.empty) {
      return null;
    }

    return {
      id: querySnapshot.docs[0].id,
      ...querySnapshot.docs[0].data()
    };
  } catch (error) {
    console.error('Error fetching analysis:', error);
    throw new Error('Failed to fetch analysis');
  }
}

/**
 * Get analysis by ID
 * @param {string} analysisId - Analysis ID
 * @returns {Promise<object|null>} Analysis data or null if not found
 */
export async function getAnalysisById(analysisId) {
  try {
    const q = query(
      collection(db, ANALYSES_COLLECTION),
      where('analysisId', '==', analysisId),
      limit(1)
    );

    const querySnapshot = await getDocs(q);
    
    if (querySnapshot.empty) {
      return null;
    }

    return {
      id: querySnapshot.docs[0].id,
      ...querySnapshot.docs[0].data()
    };
  } catch (error) {
    console.error('Error fetching analysis by ID:', error);
    throw new Error('Failed to fetch analysis');
  }
}
