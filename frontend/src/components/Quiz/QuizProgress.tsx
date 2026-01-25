import React from 'react'
import { QuizProgress as QuizProgressType } from '../../services/api'

interface QuizProgressProps {
  progress: QuizProgressType
}

const QuizProgress: React.FC<QuizProgressProps> = ({ progress }) => {
  const progressPercentage = progress.total_questions > 0 
    ? (progress.current_index / progress.total_questions) * 100 
    : 0

  const accuracyPercentage = progress.current_index > 0 && progress.correct_answers !== undefined
    ? (progress.correct_answers / progress.current_index) * 100
    : 0

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Progress</span>
          <span>{progress.current_index} of {progress.total_questions} questions</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-2xl font-bold text-gray-900">
            {progress.current_index}
          </div>
          <div className="text-sm text-gray-600">Answered</div>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-2xl font-bold text-gray-900">
            {progress.total_questions - progress.current_index}
          </div>
          <div className="text-sm text-gray-600">Remaining</div>
        </div>

        {progress.correct_answers !== undefined && (
          <>
            <div className="bg-green-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-green-600">
                {progress.correct_answers}
              </div>
              <div className="text-sm text-green-700">Correct</div>
            </div>
            
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-blue-600">
                {Math.round(accuracyPercentage)}%
              </div>
              <div className="text-sm text-blue-700">Accuracy</div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default QuizProgress