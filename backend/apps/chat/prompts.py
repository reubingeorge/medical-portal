"""
Enhanced chat prompt system with modular, efficient design.
"""
from django.utils.translation import gettext_lazy as _


class PromptBuilder:
    """Modular prompt builder for better organization and efficiency."""
    
    def __init__(self, patient=None, language=None):
        self.patient = patient
        self.language = language
        self.patient_data = self._extract_patient_data()
    
    def _extract_patient_data(self):
        """Extract all patient data once for reuse."""
        if not self.patient:
            return {}
        
        data = {
            'patient_name': self.patient.get_full_name(),
            'doctor_name': 'Not yet assigned',
            'cancer_type': None,
            'cancer_stage': None,
            'pathology_stage': None,
            'treatment': None,
            'diagnosis_date': None,
            'language_code': 'en',
            'language_name': 'English'
        }
        
        # Get doctor info
        if hasattr(self.patient, 'assigned_doctor') and self.patient.assigned_doctor:
            data['doctor_name'] = f"Dr. {self.patient.assigned_doctor.get_full_name()}"
        
        # Get medical record info
        try:
            if hasattr(self.patient, 'medical_record') and self.patient.medical_record:
                record = self.patient.medical_record
                
                if record.cancer_type:
                    data['cancer_type'] = record.cancer_type.full_name
                
                if record.cancer_stage_text:
                    data['cancer_stage'] = record.cancer_stage_text
                
                if record.stage_grouping:
                    data['pathology_stage'] = record.stage_grouping
                
                if record.recommended_treatment:
                    data['treatment'] = record.recommended_treatment
                
                if record.diagnosis_date:
                    data['diagnosis_date'] = record.diagnosis_date.strftime('%B %d, %Y')
        except Exception:
            pass
        
        # Get language info
        if self.language:
            data['language_code'] = self.language.code
            data['language_name'] = self.language.get_code_display()
        elif hasattr(self.patient, 'language') and self.patient.language:
            data['language_code'] = self.patient.language.code
            data['language_name'] = self.patient.language.get_code_display()
        
        return data
    
    def build_system_prompt(self):
        """Build the main system prompt with all guidelines."""
        prompt = BASE_SYSTEM_PROMPT
        
        if self.patient_data:
            prompt += "\n\n" + self._build_patient_context()
        
        if self.patient_data.get('language_code') != 'en':
            prompt += "\n\n" + self._build_language_context()
        
        return prompt.strip()
    
    def _build_patient_context(self):
        """Build patient-specific context section."""
        data = self.patient_data
        
        medical_info = []
        if data['cancer_type']:
            medical_info.append(f"- Cancer Type: {data['cancer_type']}")
        if data['cancer_stage']:
            medical_info.append(f"- Cancer Stage: {data['cancer_stage']}")
        if data['pathology_stage']:
            medical_info.append(f"- Pathology Stage: {data['pathology_stage']}")
        if data['treatment']:
            medical_info.append(f"- Current Treatment: {data['treatment']}")
        if data['diagnosis_date']:
            medical_info.append(f"- Diagnosis Date: {data['diagnosis_date']}")
        
        medical_section = '\n'.join(medical_info) if medical_info else "- No specific medical information available"
        
        return f"""PATIENT CONTEXT:
- Patient Name: {data['patient_name']}
- Treating Physician: {data['doctor_name']}

Medical Information:
{medical_section}

IMPORTANT GUIDELINES FOR THIS PATIENT:
- Always refer to their doctor as {data['doctor_name']}
- Be aware of their {data['cancer_type'] or 'cancer'} diagnosis when responding
- If asked about treatments or symptoms not in your knowledge base, direct them to {data['doctor_name']}
- Never reveal their medical information unless they mention it first"""
    
    def _build_language_context(self):
        """Build language-specific context."""
        return f"""LANGUAGE PREFERENCE:
- Preferred language: {self.patient_data['language_name']}
- Communicate in {self.patient_data['language_name']} when possible
- Explain medical terms in simple {self.patient_data['language_name']} language"""
    
    def build_query_prompt(self, question, cancer_type=None):
        """Build RAG query prompt optimized for retrieval."""
        context_parts = []
        
        if cancer_type:
            context_parts.append(f"Cancer Type: {cancer_type.full_name}")
        
        if self.patient_data.get('cancer_stage'):
            context_parts.append(f"Stage: {self.patient_data['cancer_stage']}")
        
        context = " | ".join(context_parts) if context_parts else ""
        
        if context:
            return f"""Context: {context}
User Question: {question}

Find information specifically relevant to this cancer type and stage."""
        else:
            return f"User Question: {question}"
    
    def build_not_found_response(self, question):
        """Build response when no relevant information is found."""
        data = self.patient_data
        doctor = data.get('doctor_name', 'your healthcare provider')
        
        templates = {
            'en': EN_NOT_FOUND_TEMPLATE,
            'es': ES_NOT_FOUND_TEMPLATE,
            'fr': FR_NOT_FOUND_TEMPLATE,
            'ar': AR_NOT_FOUND_TEMPLATE,
            'hi': HI_NOT_FOUND_TEMPLATE
        }
        
        template = templates.get(data.get('language_code', 'en'), EN_NOT_FOUND_TEMPLATE)
        return template.format(question=question, doctor=doctor)
    
    def build_emergency_response(self):
        """Build emergency response message."""
        templates = {
            'en': EN_EMERGENCY_TEMPLATE,
            'es': ES_EMERGENCY_TEMPLATE,
            'fr': FR_EMERGENCY_TEMPLATE,
            'ar': AR_EMERGENCY_TEMPLATE,
            'hi': HI_EMERGENCY_TEMPLATE
        }
        
        language_code = self.patient_data.get('language_code', 'en')
        return templates.get(language_code, EN_EMERGENCY_TEMPLATE)


# Base Templates
BASE_SYSTEM_PROMPT = """You are a compassionate medical assistant specializing in cancer care. Your primary role is to provide accurate information based STRICTLY on the documents in your knowledge base.

CORE PRINCIPLES:

1. ACCURACY & SAFETY
   - Only provide information directly from retrieved documents
   - Never guess, infer, or extrapolate beyond what's explicitly stated
   - If information isn't available, clearly state this limitation
   - Direct patients to their healthcare provider for personalized advice

2. COMMUNICATION
   - Use warm, empathetic language appropriate for cancer patients
   - Explain medical terms in simple, accessible language
   - Be concise but thorough in your responses
   - Acknowledge the emotional challenges patients face

3. LIMITATIONS
   - You cannot provide personal medical advice
   - You cannot make diagnoses or prognoses
   - You cannot recommend specific treatments or medications
   - You cannot access real-time medical data or test results

4. EMERGENCY HANDLING
   - Recognize emergency keywords and respond immediately
   - Direct to emergency services (911) without delay
   - Provide clear, actionable emergency instructions

5. CONSISTENCY
   - Always mention that information comes from your knowledge base
   - Consistently refer patients to their doctor for personalized guidance
   - Maintain professional boundaries while being supportive"""

# Not Found Response Templates
EN_NOT_FOUND_TEMPLATE = """I apologize, but I don't have specific information about "{question}" in my current knowledge base.

This topic requires personalized medical expertise beyond the general information I can provide. I strongly recommend discussing this directly with {doctor}, who has access to your complete medical history and can provide guidance tailored to your specific situation.

If this is urgent, please contact your doctor's office immediately or seek emergency care if needed.

Is there another cancer-related topic from my knowledge base that I can help you with?"""

ES_NOT_FOUND_TEMPLATE = """Lo siento, no tengo información específica sobre "{question}" en mi base de conocimientos actual.

Este tema requiere experiencia médica personalizada más allá de la información general que puedo proporcionar. Recomiendo encarecidamente discutir esto directamente con {doctor}, quien tiene acceso a su historial médico completo y puede proporcionar orientación adaptada a su situación específica.

Si esto es urgente, comuníquese con el consultorio de su médico de inmediato o busque atención de emergencia si es necesario.

¿Hay otro tema relacionado con el cáncer en mi base de conocimientos con el que pueda ayudarlo?"""

FR_NOT_FOUND_TEMPLATE = """Je m'excuse, mais je n'ai pas d'informations spécifiques sur "{question}" dans ma base de connaissances actuelle.

Ce sujet nécessite une expertise médicale personnalisée au-delà des informations générales que je peux fournir. Je recommande fortement de discuter directement avec {doctor}, qui a accès à vos antécédents médicaux complets et peut fournir des conseils adaptés à votre situation spécifique.

Si c'est urgent, veuillez contacter immédiatement le cabinet de votre médecin ou rechercher des soins d'urgence si nécessaire.

Y a-t-il un autre sujet lié au cancer dans ma base de connaissances pour lequel je peux vous aider?"""

AR_NOT_FOUND_TEMPLATE = """أعتذر، لكن ليس لدي معلومات محددة حول "{question}" في قاعدة معرفتي الحالية.

هذا الموضوع يتطلب خبرة طبية شخصية تتجاوز المعلومات العامة التي يمكنني تقديمها. أوصي بشدة بمناقشة هذا مباشرة مع {doctor}، الذي لديه إمكانية الوصول إلى تاريخك الطبي الكامل ويمكنه تقديم إرشادات مصممة خصيصًا لحالتك الخاصة.

إذا كان هذا عاجلاً، يرجى الاتصال بعيادة طبيبك على الفور أو طلب الرعاية الطارئة إذا لزم الأمر.

هل هناك موضوع آخر متعلق بالسرطان في قاعدة معرفتي يمكنني مساعدتك فيه؟"""

HI_NOT_FOUND_TEMPLATE = """मुझे खेद है, लेकिन मेरे वर्तमान ज्ञान आधार में "{question}" के बारे में विशिष्ट जानकारी नहीं है।

इस विषय के लिए व्यक्तिगत चिकित्सा विशेषज्ञता की आवश्यकता है जो मैं प्रदान कर सकने वाली सामान्य जानकारी से परे है। मैं दृढ़ता से सलाह देता हूं कि इस पर सीधे {doctor} से चर्चा करें, जिनके पास आपके पूर्ण चिकित्सा इतिहास तक पहुंच है और जो आपकी विशिष्ट स्थिति के अनुरूप मार्गदर्शन प्रदान कर सकते हैं।

यदि यह जरूरी है, तो कृपया तुरंत अपने डॉक्टर के कार्यालय से संपर्क करें या यदि आवश्यक हो तो आपातकालीन देखभाल लें।

क्या मेरे ज्ञान आधार में कैंसर से संबंधित कोई अन्य विषय है जिसमें मैं आपकी मदद कर सकता हूं?"""

# Emergency Response Templates
EN_EMERGENCY_TEMPLATE = """I understand you may be experiencing a medical emergency. Your safety is the top priority.

PLEASE TAKE IMMEDIATE ACTION:
• Call 911 or your local emergency services NOW
• Go to the nearest emergency room
• Contact your doctor's emergency line if available

Do not wait. Emergency medical professionals can provide the immediate care you need.

Common emergency symptoms include:
- Severe chest pain or pressure
- Difficulty breathing
- Sudden severe headache
- Loss of consciousness
- Severe bleeding
- High fever with confusion

Please seek help immediately. Your oncology team can be informed after you receive emergency care."""

ES_EMERGENCY_TEMPLATE = """Entiendo que puede estar experimentando una emergencia médica. Su seguridad es la máxima prioridad.

POR FAVOR TOME ACCIÓN INMEDIATA:
• Llame al 911 o a sus servicios de emergencia locales AHORA
• Vaya a la sala de emergencias más cercana
• Contacte la línea de emergencia de su médico si está disponible

No espere. Los profesionales médicos de emergencia pueden proporcionar la atención inmediata que necesita.

Los síntomas de emergencia comunes incluyen:
- Dolor o presión severa en el pecho
- Dificultad para respirar
- Dolor de cabeza severo repentino
- Pérdida de conciencia
- Sangrado severo
- Fiebre alta con confusión

Por favor busque ayuda inmediatamente. Su equipo de oncología puede ser informado después de recibir atención de emergencia."""

FR_EMERGENCY_TEMPLATE = """Je comprends que vous pourriez vivre une urgence médicale. Votre sécurité est la priorité absolue.

VEUILLEZ PRENDRE DES MESURES IMMÉDIATES:
• Appelez le 911 ou vos services d'urgence locaux MAINTENANT
• Rendez-vous aux urgences les plus proches
• Contactez la ligne d'urgence de votre médecin si disponible

N'attendez pas. Les professionnels médicaux d'urgence peuvent fournir les soins immédiats dont vous avez besoin.

Les symptômes d'urgence courants incluent:
- Douleur ou pression thoracique sévère
- Difficulté à respirer
- Mal de tête sévère soudain
- Perte de conscience
- Saignement sévère
- Forte fièvre avec confusion

Veuillez chercher de l'aide immédiatement. Votre équipe d'oncologie peut être informée après avoir reçu des soins d'urgence."""

AR_EMERGENCY_TEMPLATE = """أفهم أنك قد تواجه حالة طبية طارئة. سلامتك هي الأولوية القصوى.

يرجى اتخاذ إجراء فوري:
• اتصل بـ 911 أو خدمات الطوارئ المحلية الآن
• اذهب إلى أقرب غرفة طوارئ  
• اتصل بخط الطوارئ الخاص بطبيبك إذا كان متاحًا

لا تنتظر. يمكن للمهنيين الطبيين في حالات الطوارئ تقديم الرعاية الفورية التي تحتاجها.

تشمل أعراض الطوارئ الشائعة:
- ألم أو ضغط شديد في الصدر
- صعوبة في التنفس
- صداع شديد مفاجئ
- فقدان الوعي
- نزيف شديد
- حمى شديدة مع ارتباك

يرجى طلب المساعدة على الفور. يمكن إبلاغ فريق الأورام الخاص بك بعد تلقي الرعاية الطارئة."""

HI_EMERGENCY_TEMPLATE = """मैं समझता हूं कि आप एक चिकित्सा आपातकाल का सामना कर रहे हो सकते हैं। आपकी सुरक्षा सर्वोच्च प्राथमिकता है।

कृपया तत्काल कार्रवाई करें:
• 911 या अपनी स्थानीय आपातकालीन सेवाओं को अभी कॉल करें
• निकटतम आपातकालीन कक्ष में जाएं
• यदि उपलब्ध हो तो अपने डॉक्टर की आपातकालीन लाइन से संपर्क करें

प्रतीक्षा न करें। आपातकालीन चिकित्सा पेशेवर आपको तत्काल देखभाल प्रदान कर सकते हैं।

सामान्य आपातकालीन लक्षण शामिल हैं:
- सीने में गंभीर दर्द या दबाव
- सांस लेने में कठिनाई
- अचानक गंभीर सिरदर्द
- चेतना की हानि
- गंभीर रक्तस्राव
- भ्रम के साथ तेज बुखार

कृपया तुरंत मदद लें। आपातकालीन देखभाल प्राप्त करने के बाद आपकी ऑन्कोलॉजी टीम को सूचित किया जा सकता है।"""