import React from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, Modal, StyleSheet, ActivityIndicator } from 'react-native';
import { BlurView } from 'expo-blur';
import { FontAwesome5 } from '@expo/vector-icons';

const SettingsWizard = ({ 
  visible, 
  setupStep, 
  serverUrl, 
  setServerUrl, 
  appType, 
  setAppType, 
  allCounters, 
  counterId, 
  setCounterId, 
  screens,
  screenId,
  setScreenId,
  handleSaveSettings, 
  setShowSettings, 
  isTesting,
  systemConfig
}) => {
  return (
    <Modal transparent visible={visible} animationType="slide">
      <View style={styles.modalOverlay}>
        <BlurView intensity={80} tint="dark" style={styles.settingsBox}>
          <Text style={styles.settingsTitle}>إعدادات الخادم</Text>
          
          {setupStep === 1 && (
            <>
              <Text style={styles.settingsSub}>أدخل عنوان خادم QMS (IP)</Text>
              <TextInput
                style={styles.input}
                placeholder="مثلاً 192.168.1.10:8000"
                placeholderTextColor="#64748b"
                value={serverUrl}
                onChangeText={setServerUrl}
                autoCapitalize="none"
                autoCorrect={false}
              />
            </>
          )}

          {setupStep === 2 && (
            <>
              <Text style={styles.settingsSub}>اختر وضع التطبيق</Text>
              <View style={styles.typeSelector}>
                <TouchableOpacity 
                  style={[styles.typeBtn, appType === 'kiosk' && { backgroundColor: systemConfig?.primary_color || '#1e40af', borderColor: systemConfig?.primary_color || '#1e40af' }]} 
                  onPress={() => setAppType('kiosk')}
                >
                  <FontAwesome5 name="print" size={24} color={appType === 'kiosk' ? 'white' : '#64748b'} />
                  <Text style={[styles.typeBtnText, appType === 'kiosk' && styles.typeBtnTextActive]}>لوحة الخدمة</Text>
                </TouchableOpacity>
                
                <TouchableOpacity 
                  style={[styles.typeBtn, appType === 'counter' && { backgroundColor: systemConfig?.primary_color || '#1e40af', borderColor: systemConfig?.primary_color || '#1e40af' }]} 
                  onPress={() => setAppType('counter')}
                >
                  <FontAwesome5 name="desktop" size={24} color={appType === 'counter' ? 'white' : '#64748b'} />
                  <Text style={[styles.typeBtnText, appType === 'counter' && styles.typeBtnTextActive]}>شاشة الكاونتر</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={[styles.typeBtn, appType === 'public' && { backgroundColor: systemConfig?.primary_color || '#1e40af', borderColor: systemConfig?.primary_color || '#1e40af' }]} 
                  onPress={() => setAppType('public')}
                >
                  <FontAwesome5 name="tv" size={24} color={appType === 'public' ? 'white' : '#64748b'} />
                  <Text style={[styles.typeBtnText, appType === 'public' && styles.typeBtnTextActive]}>لوحة الإعلانات</Text>
                </TouchableOpacity>
              </View>
            </>
          )}

          {setupStep === 3 && (
            <>
              <Text style={styles.settingsSub}>اختر رقم الكاونتر</Text>
              <ScrollView style={styles.counterList}>
                {Array.isArray(allCounters) && allCounters.map(c => (
                  <TouchableOpacity 
                    key={c.id} 
                    style={[styles.counterOption, counterId === c.id && { backgroundColor: systemConfig?.accent_color || '#eff6ff', borderColor: systemConfig?.primary_color || '#1e40af' }]}
                    onPress={() => setCounterId(c.id)}
                  >
                    <Text style={[styles.counterOptionText, counterId === c.id && { color: systemConfig?.primary_color || '#1e40af', fontWeight: '900' }]}>كاونتر {c.number}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </>
          )}

          {setupStep === 4 && (
            <>
              <Text style={styles.settingsSub}>اختر الشاشة العامة</Text>
              <ScrollView style={styles.counterList}>
                {Array.isArray(screens) && screens.map(s => (
                  <TouchableOpacity 
                    key={s.id} 
                    style={[styles.counterOption, screenId === s.token && { backgroundColor: systemConfig?.accent_color || '#eff6ff', borderColor: systemConfig?.primary_color || '#1e40af' }]}
                    onPress={() => setScreenId(s.token)}
                  >
                    <Text style={[styles.counterOptionText, screenId === s.token && { color: systemConfig?.primary_color || '#1e40af', fontWeight: '900' }]}>{s.name}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </>
          )}

          <TouchableOpacity 
            style={[styles.saveBtn, { backgroundColor: systemConfig?.primary_color || '#1e40af' }, (!serverUrl && setupStep === 1) && { opacity: 0.5 }]} 
            onPress={handleSaveSettings}
            disabled={(!serverUrl && setupStep === 1) || isTesting}
          >
            {isTesting ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.saveBtnText}>
                {setupStep === 4 || setupStep === 3 || (setupStep === 2 && appType === 'kiosk') ? 'إنهاء' : 'التالي'}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity onPress={() => setShowSettings(false)} style={styles.cancelBtn}>
            <Text style={styles.cancelBtnText}>إلغاء</Text>
          </TouchableOpacity>
        </BlurView>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.92)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  settingsBox: { width: '100%', maxWidth: 450, padding: 40, borderRadius: 24, backgroundColor: 'white', overflow: 'hidden' },
  settingsTitle: { color: '#0f172a', fontSize: 30, fontWeight: '900', textAlign: 'center' },
  settingsSub: { color: '#64748b', textAlign: 'center', marginBottom: 35, fontSize: 16, fontWeight: '500' },
  input: { backgroundColor: '#f8fafc', borderRadius: 12, padding: 20, color: '#0f172a', fontSize: 18, marginBottom: 25, borderWidth: 1, borderColor: '#e2e8f0' },
  saveBtn: { backgroundColor: '#1e40af', padding: 20, borderRadius: 12, alignItems: 'center' },
  saveBtnText: { color: 'white', fontWeight: '800', fontSize: 18, letterSpacing: 1 },
  cancelBtn: { marginTop: 15, alignItems: 'center' },
  cancelBtnText: { color: '#94a3b8', fontSize: 15 },
  typeSelector: { flexDirection: 'row', gap: 20, marginBottom: 35 },
  typeBtn: { flex: 1, backgroundColor: '#f8fafc', padding: 35, borderRadius: 16, alignItems: 'center', borderWidth: 1, borderColor: '#e2e8f0' },
  typeBtnText: { color: '#64748b', fontWeight: '800', marginTop: 15, fontSize: 17 },
  typeBtnTextActive: { color: 'white' },
  counterList: { maxHeight: 300, marginBottom: 35 },
  counterOption: { padding: 22, borderRadius: 12, backgroundColor: '#f8fafc', marginBottom: 15, borderWidth: 1, borderColor: '#e2e8f0' },
  counterOptionText: { color: '#64748b', fontWeight: '700', fontSize: 20, textAlign: 'center' },
});

export default SettingsWizard;
