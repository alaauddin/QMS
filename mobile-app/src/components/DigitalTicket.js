import React from 'react';
import { View, Text, Modal, StyleSheet } from 'react-native';

const DigitalTicket = ({ visible, lastToken, systemConfig }) => {
  return (
    <Modal transparent visible={visible} animationType="fade">
      <View style={styles.modalOverlay}>
        <View style={styles.successTicket}>
          <View style={styles.ticketTop}>
            <Text style={styles.successTitle}>شكراً لك!</Text>
            <Text style={styles.successSub}>تم إصدار تذكرتك بنجاح</Text>
          </View>
          
          <View style={styles.ticketDivider}>
            <View style={styles.dividerDot} />
            <View style={styles.dividerLine} />
            <View style={styles.dividerDot} />
          </View>

          <View style={styles.ticketBottom}>
            <Text style={styles.tokenLabel}>رقم دورك</Text>
            <View style={styles.tokenTagBox}>
              <View style={[styles.tokenTag, { backgroundColor: systemConfig?.primary_color || '#1e40af' }]}>
                <Text style={styles.tokenTagText}>{lastToken?.prefix}</Text>
              </View>
              <Text style={[styles.tokenValPremium, { color: systemConfig?.secondary_color || '#0f172a' }]}>
                {lastToken?.number}
              </Text>
            </View>
            <Text style={styles.tokenHint}>يرجى مراقبة الشاشات لمعرفة دورك</Text>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.92)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  successTicket: { width: '100%', maxWidth: 450, backgroundColor: 'white', borderRadius: 32, overflow: 'hidden' },
  ticketTop: { padding: 40, alignItems: 'center', backgroundColor: '#fdfdfd' },
  ticketDivider: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fdfdfd' },
  dividerDot: { width: 30, height: 30, borderRadius: 15, backgroundColor: 'rgba(15, 23, 42, 0.92)', marginHorizontal: -15 },
  dividerLine: { flex: 1, height: 1, borderStyle: 'dashed', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 1 },
  ticketBottom: { padding: 40, alignItems: 'center', backgroundColor: 'white' },
  successTitle: { fontSize: 32, fontWeight: '900', color: '#0f172a', letterSpacing: 2 },
  successSub: { fontSize: 16, color: '#64748b', marginTop: 5, fontWeight: '500' },
  tokenLabel: { color: '#64748b', fontSize: 14, fontWeight: '800', letterSpacing: 3, marginBottom: 20 },
  tokenTagBox: { flexDirection: 'row', alignItems: 'center', gap: 20 },
  tokenTag: { backgroundColor: '#0f172a', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 8 },
  tokenTagText: { color: 'white', fontSize: 24, fontWeight: '900' },
  tokenValPremium: { fontSize: 100, fontWeight: '900' },
  tokenHint: { color: '#94a3b8', fontSize: 13, marginTop: 30, textAlign: 'center', fontWeight: '500' },
});

export default DigitalTicket;
