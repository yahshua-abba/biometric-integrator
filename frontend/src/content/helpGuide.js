import sections from './helpGuide.json'
export const helpSections = sections
export const guideText = 'Biometric Integration - User Guide\n\n' + sections.map(section => section.title + '\n' + section.items.map(item => '- ' + item).join('\n')).join('\n\n')
export const guidePrompt = 'Use this Biometric Integration user guide to answer my questions in simple language. You cannot inspect my app or Payroll. Do not invent missing product behavior. First ask what I need help with.\n\n' + guideText
export const chatGptGuideUrl = 'https://chatgpt.com/?q=' + encodeURIComponent(guidePrompt)
