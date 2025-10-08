import { AlertTriangle, Shield, Info, Phone } from 'lucide-react'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from './ui/dialog'

interface MedicalDisclaimerProps {
  isOpen: boolean
  onClose: () => void
}

const MedicalDisclaimer = ({ isOpen, onClose }: MedicalDisclaimerProps) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogClose onClick={onClose} />
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-6 w-6" />
            Important Medical Disclaimer
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 text-sm leading-relaxed">
          {/* Main Disclaimer */}
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-red-700 dark:text-red-300 mb-2">
                  This AI is NOT a Licensed Medical Professional
                </h3>
                <p className="text-red-600 dark:text-red-400">
                  This chatbot is an artificial intelligence system and is <strong>not a doctor, nurse, pharmacist, or any other licensed healthcare provider</strong>. 
                  It cannot and does not provide medical advice, diagnoses, or treatment recommendations.
                </p>
              </div>
            </div>
          </div>

          {/* Educational Purposes */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-blue-700 dark:text-blue-300 mb-2">
                  For Educational Purposes Only
                </h3>
                <p className="text-blue-600 dark:text-blue-400">
                  All information provided by this AI is for <strong>general educational and informational purposes only</strong>. 
                  It is not intended to replace professional medical advice, diagnosis, or treatment from a qualified healthcare provider.
                </p>
              </div>
            </div>
          </div>

          {/* Accuracy Warning */}
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-yellow-700 dark:text-yellow-300 mb-2">
                  Potential for Inaccuracies
                </h3>
                <p className="text-yellow-600 dark:text-yellow-400">
                  AI responses may contain <strong>errors, be incomplete, or outdated</strong>. AI models are known to experience "hallucinations" 
                  and may provide incorrect information. Always verify any health-related information with qualified medical professionals.
                </p>
              </div>
            </div>
          </div>

          {/* User Responsibility */}
          <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Your Responsibility
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  You are responsible for <strong>independently verifying</strong> any information provided and making your own healthcare decisions. 
                  <strong>Always consult with a qualified medical professional</strong> before making any health-related decisions or changes to your treatment.
                </p>
              </div>
            </div>
          </div>

          {/* Emergency Clause */}
          <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-700 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Phone className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-red-700 dark:text-red-300 mb-2">
                  ⚠️ MEDICAL EMERGENCIES
                </h3>
                <p className="text-red-600 dark:text-red-400 mb-3">
                  <strong>DO NOT use this chatbot for medical emergencies</strong>. If you are experiencing a medical emergency or crisis, 
                  immediately contact:
                </p>
                <ul className="text-red-600 dark:text-red-400 space-y-1 ml-4">
                  <li>• <strong>Emergency Services: 911 (US) or your local emergency number</strong></li>
                  <li>• Your healthcare provider</li>
                  <li>• Poison Control: 1-800-222-1222 (US)</li>
                  <li>• Crisis hotlines if experiencing mental health emergencies</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Data Privacy */}
          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-purple-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-purple-700 dark:text-purple-300 mb-2">
                  Data Privacy & Security
                </h3>
                <p className="text-purple-600 dark:text-purple-400 mb-2">
                  Your conversations may be stored and analyzed to improve our services. We implement security measures to protect your data, 
                  but no system is completely secure.
                </p>
                <p className="text-purple-600 dark:text-purple-400">
                  <strong>Avoid sharing sensitive personal health information, social security numbers, or other highly confidential data.</strong>
                  {/* Note: In a real app, you would link to an actual privacy policy */}
                  <span className="block mt-1">
                    For complete details, please review our Privacy Policy.
                  </span>
                </p>
              </div>
            </div>
          </div>

          {/* Data Source Limitations */}
          <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Data Source Limitations
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  This AI's responses are based on training data that may not include the <strong>most recent medical research, 
                  drug approvals, treatment guidelines, or safety information</strong>. Medical knowledge evolves rapidly, 
                  and this system may not have access to the latest developments in healthcare.
                </p>
              </div>
            </div>
          </div>

          {/* Acknowledgment */}
          <div className="border-t pt-4 mt-6">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              By continuing to use this service, you acknowledge that you have read, understood, and agree to these terms and limitations.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
          <Button onClick={onClose} className="px-6">
            I Understand, Continue
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default MedicalDisclaimer
