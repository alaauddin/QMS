import axios from 'axios';

const apiClient = axios.create({
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  }
});

/**
 * Updates the base URL for the API client dynamically.
 */
export const updateBaseUrl = (url) => {
  apiClient.defaults.baseURL = url;
};

export const testConnection = async (url) => {
  try {
    const response = await axios.get(`${url}/qms/api/kiosk/`, { timeout: 3000 });
    return response.status === 200;
  } catch (e) {
    return false;
  }
};

export const getKioskData = async () => {
  try {
    const response = await apiClient.get('/qms/api/kiosk/');
    return response.data;
  } catch (error) {
    console.error('API Error (Kiosk Data):', error);
    throw error;
  }
};

export const takeToken = async (serviceId) => {
  try {
    const response = await apiClient.post(`/qms/api/kiosk/take-token/${serviceId}/`);
    return response.data;
  } catch (error) {
    console.error('API Error (Take Token):', error);
    throw error;
  }
};

export const getCounters = async () => {
  try {
    const response = await apiClient.get('/qms/api/counters/');
    return response.data;
  } catch (error) {
    console.error('API Error (Get Counters):', error);
    throw error;
  }
};

export const getCurrentToken = async (counterId) => {
  try {
    const response = await apiClient.get(`/qms/api/counters/current-token/${counterId}/`);
    return response.data;
  } catch (error) {
    console.error('API Error (Get Current Token):', error);
    throw error;
  }
};

export const getSystemConfig = async () => {
  try {
    const response = await apiClient.get('/qms/api/config/');
    return response.data;
  } catch (error) {
    console.error('Config Fetch Error:', error);
    return null;
  }
};

export const getScreens = async () => {
  try {
    const response = await apiClient.get('/qms/api/screens/');
    return response.data;
  } catch (error) {
    console.error('API Error (Get Screens):', error);
    throw error;
  }
};

export const getScreenData = async (token) => {
  try {
    const response = await apiClient.get(`/qms/api/screens/data/${token}/`);
    return response.data;
  } catch (error) {
    console.error('API Error (Get Screen Data):', error);
    throw error;
  }
};

export default apiClient;
