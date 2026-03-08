import { initializeApp } from "firebase/app";
import { getDatabase } from "firebase/database";
import { getAnalytics } from "firebase/analytics";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB6z3augdnPrUTp8WAFjsy2cOaMD1-Xq2w",
  authDomain: "project-6875119370382367601.firebaseapp.com",
  projectId: "project-6875119370382367601",
  storageBucket: "project-6875119370382367601.firebasestorage.app",
  messagingSenderId: "500119574108",
  appId: "1:500119574108:web:fa418eed53768e026cb899",
  measurementId: "G-Q42ZMYVXM9",
  databaseURL: "https://project-6875119370382367601-default-rtdb.firebaseio.com"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const analytics = typeof window !== "undefined" ? getAnalytics(app) : null;
export const database = getDatabase(app);
