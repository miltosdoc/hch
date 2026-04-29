import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
});

export const getFleetStatus = () => api.get('/devices/fleet-status');
export const getCapacity = () => api.get('/schedule/capacity');
export const suggestSlot = (examType, returnType, date) => 
  api.get('/schedule/suggest', { params: { exam_type: examType, return_type: returnType, target_date: date }});
export const getRevenueSuggestions = () => api.get('/schedule/revenue-suggestions');
export const checkoutDevice = (deviceId, payload) => 
  api.post(`/devices/${deviceId}/checkout`, payload);
export const checkinDevice = (deviceId) => 
  api.post(`/devices/${deviceId}/checkin`);

export const createDevice = (deviceCode, serialNumber, chainType) => 
  api.post('/devices/create', { 
    device_code: deviceCode,
    serial_number: serialNumber || null,
    chain_type: chainType || null,
  });
export const editDevice = (deviceId, updates) =>
  api.patch(`/devices/${deviceId}`, updates);
export const deleteDevice = (deviceId) => 
  api.delete(`/devices/${deviceId}`);

export const fetchExams = () => api.get('/exams');
export const getActiveClinic = () => api.get('/exams/active-clinic');
export const syncWebdocExams = () => api.post('/exams/webdoc-sync');
export const reassignExamDevice = (examId, newDeviceId) =>
  api.patch(`/exams/${examId}/reassign`, { new_device_id: newDeviceId });
export const setExamReturnType = (examId, returnType) =>
  api.patch(`/exams/${examId}/return-type`, { return_type: returnType });
export const setExamDuration = (examId, days) =>
  api.patch(`/exams/${examId}/duration`, { duration_days: days });
export const checkoutExam = (examId) =>
  api.post(`/exams/${examId}/checkout`);
export const checkinExam = (examId) =>
  api.post(`/exams/${examId}/checkin`);
export const reactivateExam = (examId) =>
  api.post(`/exams/${examId}/reactivate`);
export const postponeExam = (examId, newDate) =>
  api.patch(`/exams/${examId}/postpone`, { new_return_date: newDate });

export const getPostalActive = () => api.get('/postal/active');
export const getPostalStats = () => api.get('/postal/statistics');
export const markPostalTransit = (examId) => api.post(`/postal/${examId}/transit`);
export const markPostalReceived = (examId) => api.post(`/postal/${examId}/receive`);

export default api;
