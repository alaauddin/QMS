import * as Print from 'expo-print';

/**
 * Prints the HTML fragment received from the API.
 * This HTML includes styles for 80mm thermal printers.
 */
export const printTicket = async (html) => {
  try {
    // Step 1: Generate a PDF with exact width and dynamic height
    // 80mm = 227pt. By omitting height (or setting to undefined), 
    // we tell the engine to shrink the page to the content size.
    const { uri } = await Print.printToFileAsync({
      html: html,
      width: 227,
    });

    // Step 2: Print the specific PDF file
    await Print.printAsync({
      uri: uri
    });
  } catch (error) {
    console.error('Printing failed:', error);
    throw error;
  }
};
