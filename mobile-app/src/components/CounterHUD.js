import React from 'react';
import { View, Text, Animated, ActivityIndicator, StyleSheet } from 'react-native';

const CounterHUD = ({ currentToken, counterId, allCounters, systemConfig, pulseAnim, isConnected }) => {
  return (
    <View style={[styles.counterLandscape, { backgroundColor: systemConfig?.secondary_color || '#020617' }]}>
      <View style={[styles.landscapeLeft, { borderRightWidth: 1, borderRightColor: 'rgba(255,255,255,0.05)' }]}>
        <View style={styles.sidebarHeader}>
          <View style={[styles.statusDot, { backgroundColor: isConnected ? '#10b981' : '#ef4444' }]} />
          <Text style={[styles.statusText, { color: isConnected ? '#64748b' : '#ef4444' }]}>
            {isConnected ? 'النظام نشط' : 'انقطع الاتصال'}
          </Text>
        </View>
        
        <Text style={styles.counterNumberLabel}>رقم الكاونتر</Text>
        <Text style={[styles.counterNumberValue, { color: systemConfig?.primary_color || 'white' }]}>
          {(Array.isArray(allCounters) ? allCounters.find(c => c.id === counterId) : null)?.number || counterId}
        </Text>
        
        <View style={styles.sidebarFooter}>
          <Text style={styles.sidebarFooterText}>{systemConfig?.system_name || 'QMS'}</Text>
        </View>
      </View>

      <View style={styles.landscapeRight}>
        <Animated.View style={[
          styles.servingCardLandscape, 
          { 
            backgroundColor: 'rgba(15, 23, 42, 0.4)',
            borderColor: systemConfig?.primary_color || 'rgba(30, 64, 175, 0.3)',
            shadowColor: systemConfig?.primary_color || '#1e40af',
          }
        ]}>
          <View style={styles.hudLabelBox}>
            <Text style={styles.servingLabel}>يتم خدمته الآن</Text>
          </View>

          {currentToken ? (
            <View style={styles.tokenContainer}>
              <Animated.View style={[styles.glowRing, { opacity: pulseAnim, borderColor: systemConfig?.primary_color || '#1e40af' }]} />
              <View style={[styles.tokenTagLarge, { backgroundColor: systemConfig?.primary_color || '#1e40af' }]}>
                <Text style={styles.tokenTagTextLarge}>{currentToken.prefix}</Text>
              </View>
              <Text style={[styles.tokenValueLarge, { color: 'white', textShadowColor: systemConfig?.primary_color || '#1e40af' }]}>
                {currentToken.number}
              </Text>
              <View style={styles.serviceBoxHud}>
                <Text style={styles.serviceNameLarge}>{currentToken.service_name}</Text>
              </View>
            </View>
          ) : (
            <View style={styles.waitingContainer}>
              <ActivityIndicator color={systemConfig?.primary_color || '#1e40af'} size="large" style={{ marginBottom: 30 }} />
              <Text style={styles.waitingLabel}>في انتظار العميل التالي</Text>
            </View>
          )}
        </Animated.View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  counterLandscape: { flex: 1, flexDirection: 'row-reverse', alignItems: 'center', backgroundColor: '#020617', padding: 20 },
  landscapeLeft: { flex: 0.8, alignItems: 'center', justifyContent: 'center', height: '100%', paddingVertical: 40 },
  landscapeRight: { flex: 2.2, height: '100%', padding: 30, justifyContent: 'center' },
  sidebarHeader: { position: 'absolute', top: 40, flexDirection: 'row-reverse', alignItems: 'center', gap: 10 },
  statusDot: { width: 8, height: 8, borderRadius: 4, shadowColor: '#10b981', shadowOffset: { width: 0, height: 0 }, shadowOpacity: 1, shadowRadius: 10 },
  statusText: { color: '#64748b', fontSize: 13, fontWeight: '900', letterSpacing: 1 },
  sidebarFooter: { position: 'absolute', bottom: 40 },
  sidebarFooterText: { color: 'rgba(255,255,255,0.1)', fontSize: 32, fontWeight: '900', letterSpacing: 10 },
  counterNumberLabel: { color: 'rgba(255,255,255,0.2)', fontSize: 20, fontWeight: '900', letterSpacing: 2, marginBottom: 10 },
  counterNumberValue: { fontSize: 140, fontWeight: '900', marginTop: -10, letterSpacing: -5 },
  servingCardLandscape: { flex: 1, borderRadius: 40, padding: 40, alignItems: 'center', justifyContent: 'center', borderWidth: 1, shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.4, shadowRadius: 50 },
  hudLabelBox: { position: 'absolute', top: 30, paddingHorizontal: 20, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  servingLabel: { color: 'rgba(255,255,255,0.3)', fontSize: 22, fontWeight: '900', letterSpacing: 2 },
  glowRing: { position: 'absolute', width: 450, height: 450, borderRadius: 225, borderWidth: 2, opacity: 0.2 },
  tokenContainer: { alignItems: 'center', width: '100%', justifyContent: 'center' },
  tokenTagLarge: { paddingHorizontal: 40, paddingVertical: 14, borderRadius: 12, marginBottom: 25 },
  tokenTagTextLarge: { color: 'white', fontSize: 50, fontWeight: '900' },
  tokenValueLarge: { fontSize: 220, fontWeight: '900', lineHeight: 220, textShadowOffset: {width: 0, height: 0}, textShadowRadius: 30 },
  serviceBoxHud: { marginTop: 20, paddingHorizontal: 30, paddingVertical: 8, backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 100 },
  serviceNameLarge: { color: '#64748b', fontSize: 26, fontWeight: '900', letterSpacing: 2 },
  waitingContainer: { alignItems: 'center' },
  waitingLabel: { color: 'rgba(255,255,255,0.2)', fontSize: 28, fontWeight: '900', textAlign: 'center', letterSpacing: 2 },
});

export default CounterHUD;
