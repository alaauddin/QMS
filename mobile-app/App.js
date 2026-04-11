import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, Text, View, FlatList, TouchableOpacity, 
  Dimensions, Alert, ActivityIndicator, SafeAreaView, Animated, Vibration 
} from 'react-native';
import * as FileSystem from 'expo-file-system';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import * as ScreenOrientation from 'expo-screen-orientation';
import { FontAwesome5 } from '@expo/vector-icons';
import { Audio } from 'expo-av';

// Modular Components
import ServiceCard from './src/components/ServiceCard';
import HUDBackground from './src/components/HUDBackground';
import DigitalTicket from './src/components/DigitalTicket';
import CounterHUD from './src/components/CounterHUD';
import SettingsWizard from './src/components/SettingsWizard';
import DigitalSignage from './src/components/DigitalSignage';

// API Utilities
import { 
  getKioskData, takeToken, updateBaseUrl, testConnection, 
  getCounters, getCurrentToken, getSystemConfig,
  getScreens, getScreenData
} from './utils/api';
import { printTicket } from './utils/printing';

const { width } = Dimensions.get('window');
const COLUMN_COUNT = 2; // Fixed as requested

export default function App() {
  const [loading, setLoading] = useState(true);
  const [services, setServices] = useState([]);
  const [serverUrl, setServerUrl] = useState('');
  const [appType, setAppType] = useState('kiosk');
  const [counterId, setCounterId] = useState(null);
  const [screenId, setScreenId] = useState(null); // Slug/Token
  const [showSettings, setShowSettings] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [lastToken, setLastToken] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [setupStep, setSetupStep] = useState(1);
  const [allCounters, setAllCounters] = useState([]);
  const [screens, setScreens] = useState([]);
  const [currentToken, setCurrentToken] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0); 
  const [isConnected, setIsConnected] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  // Audio Player for Announcements (Reliable Filesystem Version)
  const playAnnouncement = async (base64Audio) => {
    if (!base64Audio || base64Audio.length < 100) return; 
    const fileUri = `${FileSystem.cacheDirectory}announcement.mp3`;
    
    try {
      // 1. Write to temporary file
      await FileSystem.writeAsStringAsync(fileUri, base64Audio, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // 2. Vibrate to confirm reception
      Vibration.vibrate([0, 100, 50, 100]); 

      // 3. Play from file
      const { sound } = await Audio.Sound.createAsync(
        { uri: fileUri },
        { shouldPlay: true, volume: 1.0 }
      );
      
      sound.setOnPlaybackStatusUpdate(async (status) => {
        if (status.didJustFinish) {
          await sound.unloadAsync();
          // Optional: delete file after play
          await FileSystem.deleteAsync(fileUri, { idempotent: true });
        }
      });
    } catch (error) {
      console.error('Playback Error (Filesystem):', error);
      // Fallback to direct URI if filesystem fails
      try {
        const { sound } = await Audio.Sound.createAsync(
          { uri: `data:audio/mpeg;base64,${base64Audio}` },
          { shouldPlay: true }
        );
      } catch (e) {}
    }
  };
  const [systemConfig, setSystemConfig] = useState(null);
  const [isTesting, setIsTesting] = useState(false);
  
  const pulseAnim = React.useRef(new Animated.Value(0.4)).current;

  // Pulse Animation for Counter HUD
  useEffect(() => {
    if (appType === 'counter') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 0.4, duration: 2000, useNativeDriver: true }),
        ])
      ).start();
    }
  }, [appType]);

  // Handle Orientation
  useEffect(() => {
    async function changeOrientation() {
      if (appType === 'counter') {
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT);
      } else if (appType === 'public') {
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT);
      } else {
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP);
      }
    }
    changeOrientation();
    
    // Setup Audio Mode globally once
    const setupAudio = async () => {
      try {
        await Audio.setAudioModeAsync({
          playsInSilentModeIOS: true,
          staysActiveInBackground: true,
          shouldRouteThroughEarpieceAndroid: false,
        });
      } catch (e) {}
    };
    setupAudio();
  }, [appType]);

  useEffect(() => {
    initApp();
  }, []);

  const initApp = async () => {
    const savedUrl = await SecureStore.getItemAsync('API_URL');
    const savedType = await SecureStore.getItemAsync('APP_TYPE');
    const savedCounter = await SecureStore.getItemAsync('COUNTER_ID');
    const savedScreen = await SecureStore.getItemAsync('SCREEN_ID');
    const savedConfig = await SecureStore.getItemAsync('SYSTEM_CONFIG');

    if (savedConfig) setSystemConfig(JSON.parse(savedConfig));
    if (savedUrl) {
      setServerUrl(savedUrl);
      updateBaseUrl(savedUrl);
      loadConfig();
      if (savedType) setAppType(savedType);
      if (savedCounter) setCounterId(parseInt(savedCounter));
      if (savedScreen) setScreenId(savedScreen);
      setShowSettings(false);
      loadData();
    } else {
      setShowSettings(true);
      setLoading(false);
    }
  };

  const loadConfig = async () => {
    try {
      const config = await getSystemConfig();
      if (config) {
        setSystemConfig(config);
        await SecureStore.setItemAsync('SYSTEM_CONFIG', JSON.stringify(config));
      }
    } catch (e) { console.error('Config error:', e); }
  };

  const loadData = async () => {
    // Only show big loader if we have no services and we are in kiosk mode
    if (appType === 'kiosk' && !services.length) {
      setLoading(true);
    }
    
    try {
      if (appType === 'kiosk') {
        const data = await getKioskData();
        setIsConnected(true);
        // Only update if changed
        if (JSON.stringify(services) !== JSON.stringify(data.services)) {
          setServices(data.services || []);
        }
      } else if (appType === 'counter' && counterId) {
        const result = await getCounters();
        setIsConnected(true);
        setAllCounters(result.counters || []);
        const token = await getCurrentToken(counterId);
        if (token.success && token.has_token) {
          setCurrentToken(token.token);
        } else {
          setCurrentToken(null);
        }
      }
    } catch (e) {
      console.error('Load Error:', e);
      setIsConnected(false);
      setErrorMsg('Cannot reach server');
    } finally {
      setLoading(false);
    }
  };

  const handleServicePress = async (serviceId) => {
    setProcessing(true);
    try {
      const res = await takeToken(serviceId);
      if (res.success) {
        setLastToken(res.token);
        setShowSuccess(true);
        loadData();
        setTimeout(() => setShowSuccess(false), 5000);
        if (res.print_html) {
          await printTicket(res.print_html);
        }
      }
    } catch (e) { 
      console.error('Print Error:', e);
      Alert.alert('خطأ في الطباعة', 'فشل في إصدار أو طباعة التذكرة. يرجى مراجعة الاتصال.'); 
    }
    finally { setProcessing(false); }
  };

  const handleSaveSettings = async () => {
    if (!serverUrl) return;
    
    if (setupStep === 1) {
      setIsTesting(true);
      let cleanUrl = serverUrl.trim().replace(/\/$/, ""); 
      if (!cleanUrl.startsWith('http')) cleanUrl = 'http://' + cleanUrl;

      const ok = await testConnection(cleanUrl);
      if (ok) {
        await SecureStore.setItemAsync('API_URL', cleanUrl);
        updateBaseUrl(cleanUrl);
        setServerUrl(cleanUrl);
        await loadConfig();
        setSetupStep(2);
      } else {
        Alert.alert('Connection Failed', 'Could not verify server.');
      }
      setIsTesting(false);
    } else if (setupStep === 2) {
      if (appType === 'kiosk') {
        await SecureStore.setItemAsync('APP_TYPE', 'kiosk');
        await SecureStore.deleteItemAsync('COUNTER_ID');
        await SecureStore.deleteItemAsync('SCREEN_ID');
        setShowSettings(false);
        setSetupStep(1);
        loadData();
      } else if (appType === 'counter') {
        setIsTesting(true);
        try {
          const result = await getCounters();
          setAllCounters(result.counters || []);
          setSetupStep(3);
        } catch (e) { Alert.alert('Error', 'Could not fetch counters'); }
        setIsTesting(false);
      } else {
        // Public Mode
        setIsTesting(true);
        try {
          const result = await getScreens();
          setScreens(result.screens || []);
          setSetupStep(4);
        } catch (e) { Alert.alert('Error', 'Could not fetch screens'); }
        setIsTesting(false);
      }
    } else if (setupStep === 3) {
      if (counterId) {
        await SecureStore.setItemAsync('APP_TYPE', 'counter');
        await SecureStore.setItemAsync('COUNTER_ID', counterId.toString());
        await SecureStore.deleteItemAsync('SCREEN_ID');
        setShowSettings(false);
        setSetupStep(1);
        loadData();
      }
    } else if (setupStep === 4) {
      if (screenId) {
        await SecureStore.setItemAsync('APP_TYPE', 'public');
        await SecureStore.setItemAsync('SCREEN_ID', screenId);
        await SecureStore.deleteItemAsync('COUNTER_ID');
        setShowSettings(false);
        setSetupStep(1);
        loadData();
      }
    }
  };

  // Real-time updates via WebSockets
  useEffect(() => {
    let active = true;
    let ws = null;
    let reconnectTimeout = null;

    const connect = () => {
      if (!serverUrl || showSettings || !active) return;

      const protocol = serverUrl.startsWith('https') ? 'wss://' : 'ws://';
      const host = serverUrl.replace(/^https?:\/\//, '');
      const targetId = appType === 'counter' ? counterId : 1;
      
      if (!targetId) return;

      const wsUrl = `${protocol}${host}/ws/counter/${targetId}/`;
      console.log('Connecting to WS:', wsUrl);
      
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!active) return;
        console.log('WS Connection Established:', wsUrl);
        setIsConnected(true);
      };
      
      ws.onmessage = (e) => {
        if (!active) return;
        const data = JSON.parse(e.data);
        if (data.type === 'token_called' && appType === 'counter') {
          setCurrentToken({
            number: data.token,
            prefix: data.service,
            service_name: data.service_name,
          });
        } else if (data.type === 'token_cleared' && appType === 'counter') {
          setCurrentToken(null);
        } else if (data.type === 'queue_changed' || data.type === 'token_called' || data.type === 'token_audio') {
          console.log('Queue Change Detected / Audio received...');
          const audioData = data.audio;
          if (audioData) {
             // Always play if received (Kiosk, Screen, or Counter)
             playAnnouncement(audioData);
          }
          setRefreshTrigger(prev => prev + 1);
          
          if (appType !== 'public') {
             if (reconnectTimeout) clearTimeout(reconnectTimeout); 
             reconnectTimeout = setTimeout(() => {
                if (active) loadData();
             }, 500); 
          }
        }
      };

      ws.onerror = (err) => {
        if (!active) return;
        console.error('WS Connection Error:', err);
        setIsConnected(false);
      };
      
      ws.onclose = (e) => {
        if (!active) return;
        console.log('WS Connection Closed, Reconnecting in 5s...', e.reason);
        setIsConnected(false);
        reconnectTimeout = setTimeout(() => {
          if (active) connect();
        }, 5000);
      };
    };

    connect();
    return () => {
      active = false;
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [appType, counterId, serverUrl, showSettings]);

  if (loading && !showSettings) {
    return (
      <View style={[styles.centered, { backgroundColor: systemConfig?.accent_color || '#f1f5f9' }]}>
        <ActivityIndicator size="large" color={systemConfig?.primary_color || '#2563eb'} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: appType === 'kiosk' ? (systemConfig?.accent_color || '#f1f5f9') : (systemConfig?.secondary_color || '#020617') }]}>
      <StatusBar style={appType === 'kiosk' ? 'dark' : 'light'} translucent={true} backgroundColor="transparent" />
      
      {!isConnected && (
        <SafeAreaView style={{ backgroundColor: '#ef4444' }}>
          <View style={{ paddingVertical: 4, alignItems: 'center' }}>
            <Text style={{ color: 'white', fontSize: 12, fontWeight: 'bold' }}>
              ⚠️ {errorMsg || 'Offline - Reconnecting...'}
            </Text>
          </View>
        </SafeAreaView>
      )}
      
      {appType === 'counter' && <HUDBackground />}
      
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.topActions}>
          <TouchableOpacity onPress={() => setShowSettings(true)} style={styles.gearBtn}>
            <FontAwesome5 name="cog" size={24} color={appType === 'kiosk' ? 'rgba(15, 23, 42, 0.2)' : 'rgba(255,255,255,0.4)'} />
          </TouchableOpacity>
        </View>

        {appType === 'kiosk' ? (
          <>
            <View style={styles.header}>
              <Text style={styles.welcomeText}>{systemConfig?.system_name || 'مرحباً بك'}</Text>
              <View style={[styles.headerUnderline, { backgroundColor: systemConfig?.primary_color || '#1e40af' }]} />
              <Text style={styles.instructionText}>الرجاء اختيار الخدمة للحصول على تذكرتك</Text>
            </View>

            <FlatList
              data={services}
              renderItem={({ item }) => (
                <ServiceCard 
                  item={item} 
                  systemConfig={systemConfig} 
                  handleServicePress={handleServicePress}
                  processing={processing}
                  isConnected={isConnected}
                />
              )}
              keyExtractor={item => item.id.toString()}
              numColumns={COLUMN_COUNT}
              contentContainerStyle={styles.listContent}
              style={styles.list}
            />
          </>
        ) : appType === 'counter' ? (
          <CounterHUD 
            currentToken={currentToken}
            counterId={counterId}
            allCounters={allCounters}
            systemConfig={systemConfig}
            pulseAnim={pulseAnim}
            isConnected={isConnected}
          />
        ) : (
          <DigitalSignage 
            screenId={screenId}
            refreshTrigger={refreshTrigger}
            systemConfig={systemConfig}
            isConnected={isConnected}
          />
        )}
      </SafeAreaView>

      <SettingsWizard 
        visible={showSettings}
        setupStep={setupStep}
        serverUrl={serverUrl}
        setServerUrl={setServerUrl}
        appType={appType}
        setAppType={setAppType}
        allCounters={allCounters}
        counterId={counterId}
        setCounterId={setCounterId}
        screens={screens}
        screenId={screenId}
        setScreenId={setScreenId}
        handleSaveSettings={handleSaveSettings}
        setShowSettings={setShowSettings}
        isTesting={isTesting}
        systemConfig={systemConfig}
      />

      <DigitalTicket 
        visible={showSuccess}
        lastToken={lastToken}
        systemConfig={systemConfig}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  topActions: { paddingHorizontal: 30, paddingTop: 10, alignItems: 'flex-end' },
  gearBtn: { padding: 10 },
  header: { padding: 50, alignItems: 'center' },
  welcomeText: { fontSize: 32, fontWeight: '800', color: '#0f172a', letterSpacing: 2, textAlign: 'center' },
  headerUnderline: { width: 30, height: 3, marginTop: 12, borderRadius: 2 },
  instructionText: { fontSize: 15, color: '#64748b', marginTop: 15, fontWeight: '500', textAlign: 'center' },
  list: { flex: 1 },
  listContent: { padding: 30, paddingBottom: 60 },
});
