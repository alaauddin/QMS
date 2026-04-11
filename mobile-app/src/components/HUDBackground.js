import React from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';

const { height } = Dimensions.get('window');

const HUDBackground = () => {
  return (
    <>
      <View style={styles.industrialBackground}>
        {[...Array(12).keys()].map(i => (
          <View key={i} style={styles.gridLineHorizontal} />
        ))}
        {[...Array(20).keys()].map(i => (
          <View key={i} style={styles.gridLineVertical} />
        ))}
      </View>

      <View style={styles.hudCornerTopLeft} />
      <View style={styles.hudCornerTopRight} />
      <View style={styles.hudCornerBottomLeft} />
      <View style={styles.hudCornerBottomRight} />
      <View style={styles.hudTechDots} />
    </>
  );
};

const styles = StyleSheet.create({
  industrialBackground: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0.05 },
  gridLineHorizontal: { height: 1, backgroundColor: 'white', width: '100%', marginBottom: 80 },
  gridLineVertical: { width: 1, backgroundColor: 'white', height: '100%', marginRight: 80, position: 'absolute' },
  
  hudCornerTopLeft: { position: 'absolute', top: 40, left: 40, width: 40, height: 40, borderTopWidth: 2, borderLeftWidth: 2, borderColor: 'rgba(255,255,255,0.1)' },
  hudCornerTopRight: { position: 'absolute', top: 40, right: 40, width: 40, height: 40, borderTopWidth: 2, borderRightWidth: 2, borderColor: 'rgba(255,255,255,0.1)' },
  hudCornerBottomLeft: { position: 'absolute', bottom: 40, left: 40, width: 40, height: 40, borderBottomWidth: 2, borderLeftWidth: 2, borderColor: 'rgba(255,255,255,0.1)' },
  hudCornerBottomRight: { position: 'absolute', bottom: 40, right: 40, width: 40, height: 40, borderBottomWidth: 2, borderRightWidth: 2, borderColor: 'rgba(255,255,255,0.1)' },
  hudTechDots: { position: 'absolute', top: height/2, left: 20, width: 4, height: 100, backgroundColor: 'rgba(255,255,255,0.05)', borderTopWidth: 10, borderBottomWidth: 10, borderColor: 'white' },
});

export default HUDBackground;
