import React from 'react';
import { View, Text, Pressable, Animated, StyleSheet } from 'react-native';

const ServiceCard = ({ item, systemConfig, handleServicePress, processing, isConnected }) => {
  const scale = React.useRef(new Animated.Value(1)).current;

  const onPressIn = () => {
    if (!isConnected) return;
    Animated.spring(scale, {
      toValue: 0.95,
      useNativeDriver: true,
    }).start();
  };

  const onPressOut = () => {
    Animated.spring(scale, {
      toValue: 1,
      useNativeDriver: true,
    }).start();
  };

  return (
    <Animated.View style={[styles.cardContainer, { transform: [{ scale }], opacity: isConnected ? 1 : 0.6 }]}>
      <Pressable 
        onPressIn={onPressIn}
        onPressOut={onPressOut}
        onPress={() => isConnected && handleServicePress(item.id)}
        disabled={processing || !isConnected}
        style={({ pressed }) => [
          styles.card,
          { backgroundColor: isConnected ? 'white' : '#f8fafc' },
          pressed && isConnected && { backgroundColor: '#fdfdfd', shadowOpacity: 0.15, transform: [{ scale: 0.97 }] }
        ]}
      >
        {/* Top Signature Line */}
        <View style={[styles.cardSignatureLine, { backgroundColor: systemConfig?.primary_color || '#1e40af' }]} />
        
        <View style={styles.cardContent}>
          <Text style={[styles.serviceName, { color: systemConfig?.secondary_color || '#0f172a' }]}>{item.name}</Text>
          <Text style={styles.serviceDesc} numberOfLines={1}>{item.description}</Text>
        </View>

        <View style={styles.cardFooter}>
          <View style={styles.waitingPill}>
            <Text style={[styles.waitingPillText, { color: systemConfig?.primary_color || '#1e40af' }]}>
              {item.waiting_count} في الانتظار
            </Text>
          </View>
        </View>
      </Pressable>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  cardContainer: { padding: 10, flex: 0.5, height: 180 },
  card: { 
    flex: 1, 
    borderRadius: 20, 
    padding: 20, 
    backgroundColor: 'white', 
    shadowColor: '#000', 
    shadowOffset: { width: 0, height: 8 }, 
    shadowOpacity: 0.05, 
    shadowRadius: 12, 
    elevation: 4,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#f1f5f9'
  },
  cardSignatureLine: { position: 'absolute', top: 0, left: 30, right: 30, height: 3, borderBottomLeftRadius: 3, borderBottomRightRadius: 3, opacity: 0.6 },
  cardContent: { alignItems: 'center', marginBottom: 12 },
  serviceName: { fontSize: 24, fontWeight: '900', color: '#0f172a', marginBottom: 4, textAlign: 'center' },
  serviceDesc: { fontSize: 13, color: '#94a3b8', fontWeight: '500', textAlign: 'center', maxWidth: '90%' },
  cardFooter: { marginTop: 8 },
  waitingPill: { backgroundColor: '#f8fafc', paddingHorizontal: 12, paddingVertical: 4, borderRadius: 100, borderWidth: 1, borderColor: '#f1f5f9' },
  waitingPillText: { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
});

export default ServiceCard;
