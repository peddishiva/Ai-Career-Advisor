import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { getStorage } from 'firebase-admin/storage';
import { readFile } from 'fs/promises';
const serviceAccount = JSON.parse(await readFile(new URL('./serviceAccountKey.json', import.meta.url)));

let firebaseApp;
let db;
let storage;

export const initializeFirebase = async () => {
  try {
    if (!firebaseApp) {
      firebaseApp = initializeApp({
        credential: cert(serviceAccount),
        storageBucket: process.env.FIREBASE_STORAGE_BUCKET
      });
      
      // Initialize Firestore
      db = getFirestore(firebaseApp);
      
      // Initialize Storage
      storage = getStorage(firebaseApp);
      
      console.log('Firebase initialized successfully');
    }
    return { db, storage };
  } catch (error) {
    console.error('Error initializing Firebase:', error);
    throw error;
  }
};

export { db, storage };
