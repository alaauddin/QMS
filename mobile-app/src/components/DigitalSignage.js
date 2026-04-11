import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, FlatList, Image, Animated, ActivityIndicator, Dimensions, SafeAreaView } from 'react-native';
import { BlurView } from 'expo-blur';
import { FontAwesome5 } from '@expo/vector-icons';
import { getScreenData } from '../../utils/api';

const { width, height } = Dimensions.get('window');

const DigitalSignage = React.memo(({ screenId, refreshTrigger, systemConfig, isConnected }) => {
  const [publicData, setPublicData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Animation Refs
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  const fetchBoardData = async () => {
    if (!screenId) return;
    try {
      const result = await getScreenData(screenId);
      if (result.success) {
        setPublicData(result);
        triggerHighlight();
      }
    } catch (e) {
      console.error('Signage Fetch Error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const triggerHighlight = () => {
    pulseAnim.setValue(1);
    slideAnim.setValue(50);
    Animated.parallel([
       Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.05, duration: 200, useNativeDriver: true }),
          Animated.spring(pulseAnim, { toValue: 1, friction: 3, useNativeDriver: true })
       ]),
       Animated.spring(slideAnim, { toValue: 0, tension: 50, useNativeDriver: true })
    ]).start();
  };

  useEffect(() => {
    if (!publicData) setIsLoading(true);
    fetchBoardData();
    const pollTimer = setInterval(fetchBoardData, 60000);
    const clockTimer = setInterval(() => setCurrentTime(new Date()), 1000);
    
    return () => {
      clearInterval(pollTimer);
      clearInterval(clockTimer);
    };
  }, [screenId, refreshTrigger]);

  if (!publicData) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={systemConfig?.primary_color || '#1e40af'} />
        <Text style={{ color: '#64748b', marginTop: 20, fontSize: 18, fontWeight: '900' }}>جاري تحميل البيانات...</Text>
      </View>
    );
  }

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  const nowServingToken = publicData.recent && publicData.recent.length > 0 ? publicData.recent[0] : null;
  const historyTokens = publicData.recent ? publicData.recent.slice(1, 5) : [];

  return (
    <View style={styles.container}>
      {/* 1. Header Dashboard Bar */}
      <BlurView intensity={20} tint="dark" style={styles.topBar}>
         <View style={styles.logoArea}>
            <View style={[styles.connectionDot, { backgroundColor: isConnected ? '#10b981' : '#ef4444' }]} />
            <Text style={styles.headerSystemName}>{systemConfig?.system_name || 'QMS'}</Text>
         </View>
         <View style={styles.clockArea}>
            <Text style={styles.clockDigit}>{formatTime(currentTime)}</Text>
            <Text style={styles.dateLabel}>{currentTime.toLocaleDateString('ar-EG', { weekday: 'long', day: 'numeric', month: 'long' })}</Text>
         </View>
      </BlurView>

      <View style={styles.contentLayout}>
        {/* 2. Main High-Impact Section (70% Width) */}
        <View style={styles.mainPane}>
           <Text style={styles.paneSubTitle}>يتم خدمته الآن / Now Serving</Text>
           
           {nowServingToken ? (
             <Animated.View style={[
               styles.heroCard, 
               { 
                 borderColor: systemConfig?.primary_color || '#1e40af',
                 transform: [{ scale: pulseAnim }]
               }
             ]}>
                <View style={[styles.heroGlow, { backgroundColor: systemConfig?.primary_color || '#1e40af', opacity: 0.1 }]} />
                <View style={styles.heroLayout}>
                   <View style={styles.heroTokenCol}>
                      <View style={[styles.heroPrefixTag, { backgroundColor: systemConfig?.primary_color || '#1e40af' }]}>
                         <Text style={styles.heroPrefixText}>{nowServingToken.prefix}</Text>
                      </View>
                      <Text style={styles.heroTokenNum}>{nowServingToken.number}</Text>
                   </View>
                   <View style={styles.heroDivider} />
                   <View style={styles.heroCounterCol}>
                      <Text style={styles.heroCounterLabel}>كاونتر / Counter</Text>
                      <Text style={[styles.heroCounterNum, { color: systemConfig?.primary_color || '#1e40af' }]}>
                        {nowServingToken.counter_number}
                      </Text>
                   </View>
                </View>
             </Animated.View>
           ) : (
             <View style={styles.noDataCard}>
                <Text style={styles.noDataText}>في انتظار البث...</Text>
             </View>
           )}

           {/* Ads / Multimedia Area */}
           <View style={styles.mediaPane}>
              {publicData.ads && publicData.ads.length > 0 ? (
                 <Image source={{ uri: publicData.ads[0].image_url }} style={styles.adBanner} resizeMode="cover" />
              ) : (
                 <BlurView intensity={10} tint="light" style={styles.brandFallback}>
                    <FontAwesome5 name="tv" size={60} color="rgba(255,255,255,0.05)" />
                    <Text style={styles.fallbackBrandText}>{systemConfig?.system_name || 'QMS'}</Text>
                 </BlurView>
              )}
           </View>
        </View>

        {/* 3. History Ticker Section (30% Width) */}
        <View style={styles.sidePane}>
           <Text style={styles.paneSubTitle}>مناداة أخيرة / Recent</Text>
           <FlatList
             data={historyTokens}
             renderItem={({ item, index }) => (
               <Animated.View style={[styles.historyItem, { transform: [{ translateY: slideAnim }] }]}>
                  <BlurView intensity={15} tint="light" style={styles.historyBlur}>
                     <View style={styles.sideTokenInfo}>
                        <View style={[styles.sideTokenTag, { backgroundColor: systemConfig?.primary_color || '#1e40af' }]}>
                           <Text style={styles.sidePrefixText}>{item.prefix}</Text>
                        </View>
                        <Text style={styles.sideNumText}>{item.number}</Text>
                     </View>
                     <View style={styles.sideCounterInfo}>
                        <Text style={styles.sideCounterLabel}>كاونتر</Text>
                        <Text style={[styles.sideCounterVal, { color: systemConfig?.primary_color || '#1e40af' }]}>
                          {item.counter_number}
                        </Text>
                     </View>
                  </BlurView>
               </Animated.View>
             )}
             keyExtractor={(item) => item.full_token}
             scrollEnabled={false}
           />
        </View>
      </View>
    </View>
  );
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#020617' },
  topBar: { 
    height: 90, 
    flexDirection: 'row-reverse', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    paddingHorizontal: 40,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.05)',
  },
  logoArea: { flexDirection: 'row-reverse', alignItems: 'center', gap: 15 },
  connectionDot: { width: 10, height: 10, borderRadius: 5 },
  headerSystemName: { color: 'white', fontSize: 26, fontWeight: '900', letterSpacing: 2 },
  clockArea: { alignItems: 'flex-start' },
  clockDigit: { color: 'white', fontSize: 32, fontWeight: '900', letterSpacing: 1 },
  dateLabel: { color: '#64748b', fontSize: 13, fontWeight: '700' },

  contentLayout: { flex: 1, flexDirection: 'row-reverse' },
  
  // Main Pane
  mainPane: { flex: 2.2, padding: 25 },
  paneSubTitle: { color: '#64748b', fontSize: 16, fontWeight: '900', textAlign: 'right', marginBottom: 15, letterSpacing: 1 },
  heroCard: { 
    height: 380, 
    backgroundColor: 'rgba(15, 23, 42, 0.4)', 
    borderRadius: 40,
    borderWidth: 1,
    overflow: 'hidden',
    justifyContent: 'center',
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 20 },
    shadowOpacity: 0.5,
    shadowRadius: 30,
    elevation: 10
  },
  heroGlow: { position: 'absolute', top: -150, right: -150, width: 400, height: 400, borderRadius: 200 },
  heroLayout: { flexDirection: 'row-reverse', alignItems: 'center', justifyContent: 'space-around' },
  heroTokenCol: { alignItems: 'center' },
  heroPrefixTag: { paddingHorizontal: 35, paddingVertical: 12, borderRadius: 15, marginBottom: 15 },
  heroPrefixText: { color: 'white', fontSize: 45, fontWeight: '900' },
  heroTokenNum: { color: 'white', fontSize: 180, fontWeight: '900', lineHeight: 180 },
  heroDivider: { width: 1, height: '70%', backgroundColor: 'rgba(255,255,255,0.1)' },
  heroCounterCol: { alignItems: 'center' },
  heroCounterLabel: { color: '#64748b', fontSize: 22, fontWeight: '800', marginBottom: 10 },
  heroCounterNum: { fontSize: 150, fontWeight: '900' },

  mediaPane: { flex: 1, marginTop: 25, borderRadius: 35, overflow: 'hidden', backgroundColor: 'rgba(0,0,0,0.3)' },
  adBanner: { flex: 1 },
  brandFallback: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 20 },
  fallbackBrandText: { color: 'white', fontSize: 40, fontWeight: '900', opacity: 0.1 },

  // Side Pane
  sidePane: { flex: 1, borderRightWidth: 1, borderRightColor: 'rgba(255,255,255,0.05)', padding: 25, backgroundColor: 'rgba(2, 6, 23, 0.5)' },
  historyItem: { marginBottom: 15, borderRadius: 25, overflow: 'hidden' },
  historyBlur: { 
    padding: 20, 
    flexDirection: 'row-reverse', 
    justifyContent: 'space-between', 
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)'
  },
  sideTokenInfo: { flexDirection: 'row-reverse', alignItems: 'center', gap: 15 },
  sideTokenTag: { paddingHorizontal: 15, paddingVertical: 5, borderRadius: 8 },
  sidePrefixText: { color: 'white', fontSize: 22, fontWeight: '900' },
  sideNumText: { color: 'white', fontSize: 42, fontWeight: '900' },
  sideCounterInfo: { alignItems: 'center' },
  sideCounterLabel: { color: '#64748b', fontSize: 12, fontWeight: '800' },
  sideCounterVal: { fontSize: 36, fontWeight: '900' },

  noDataCard: { height: 380, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 40, borderWidth: 1, borderStyle: 'dashed', borderColor: 'rgba(255,255,255,0.1)' },
  noDataText: { color: '#64748b', fontSize: 24, fontWeight: '800' }
});

export default DigitalSignage;
