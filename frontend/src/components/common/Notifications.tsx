import { useEffect } from 'react'
import { Transition } from '@headlessui/react'
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { useUIStore } from '../../stores/uiStore'

const icons = {
  success: CheckCircleIcon,
  error: XCircleIcon,
  warning: ExclamationTriangleIcon,
  info: InformationCircleIcon,
}

const colors = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}

export default function Notifications() {
  const notifications = useUIStore((state) => state.notifications)
  const removeNotification = useUIStore((state) => state.removeNotification)

  useEffect(() => {
    notifications.forEach((notification) => {
      const duration = notification.duration || 5000
      const timer = setTimeout(() => {
        removeNotification(notification.id)
      }, duration)

      return () => clearTimeout(timer)
    })
  }, [notifications, removeNotification])

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-md">
      {notifications.map((notification) => {
        const Icon = icons[notification.type]
        const colorClass = colors[notification.type]

        return (
          <Transition
            key={notification.id}
            show={true}
            enter="transition ease-out duration-200"
            enterFrom="opacity-0 translate-y-2"
            enterTo="opacity-100 translate-y-0"
            leave="transition ease-in duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div
              className={`${colorClass} border rounded-lg shadow-lg p-4 flex items-start space-x-3`}
            >
              <Icon className="w-6 h-6 flex-shrink-0" />
              <div className="flex-1">
                <h4 className="font-medium">{notification.title}</h4>
                <p className="text-sm mt-1">{notification.message}</p>
              </div>
              <button
                onClick={() => removeNotification(notification.id)}
                className="flex-shrink-0 hover:opacity-70 focus:outline-none"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
          </Transition>
        )
      })}
    </div>
  )
}
