import { useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import Card from '../components/common/Card'
import { UserCircleIcon, ShieldCheckIcon, BellIcon } from '@heroicons/react/24/outline'

export default function Settings() {
  const user = useAuthStore((state) => state.user)
  const [activeTab, setActiveTab] = useState<'profile' | 'privacy' | 'security' | 'notifications'>(
    'profile'
  )

  const tabs = [
    { id: 'profile', name: 'Profile', icon: UserCircleIcon },
    { id: 'privacy', name: 'Privacy', icon: ShieldCheckIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Manage your account and privacy preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Tabs Sidebar */}
        <div className="lg:col-span-1">
          <Card className="p-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 text-left transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <tab.icon className="w-5 h-5" />
                  <span className="font-medium">{tab.name}</span>
                </button>
              ))}
            </nav>
          </Card>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          {activeTab === 'profile' && <ProfileSettings user={user} />}
          {activeTab === 'privacy' && <PrivacySettings />}
          {activeTab === 'security' && <SecuritySettings />}
          {activeTab === 'notifications' && <NotificationSettings />}
        </div>
      </div>
    </div>
  )
}

function ProfileSettings({ user }: { user: any }) {
  return (
    <Card title="Profile Information">
      <form className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="label">Username</label>
            <input
              type="text"
              defaultValue={user?.username}
              className="input"
              disabled
            />
          </div>

          <div>
            <label className="label">Email</label>
            <input
              type="email"
              defaultValue={user?.email}
              className="input"
            />
          </div>

          <div>
            <label className="label">First Name</label>
            <input
              type="text"
              defaultValue={user?.first_name}
              className="input"
            />
          </div>

          <div>
            <label className="label">Last Name</label>
            <input
              type="text"
              defaultValue={user?.last_name}
              className="input"
            />
          </div>
        </div>

        <button type="submit" className="btn-primary">
          Save Changes
        </button>
      </form>
    </Card>
  )
}

function PrivacySettings() {
  return (
    <Card title="Privacy Preferences">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Auto-delete messages</h4>
            <p className="text-sm text-gray-600">Automatically delete messages after 30 days</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Auto-delete documents</h4>
            <p className="text-sm text-gray-600">Automatically delete documents after 90 days</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Data anonymization</h4>
            <p className="text-sm text-gray-600">Anonymize your data in analytics</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" defaultChecked />
        </div>

        <div>
          <label className="label">Default privacy level</label>
          <select className="input">
            <option>Public</option>
            <option>Friends</option>
            <option selected>Private</option>
            <option>Hidden</option>
          </select>
        </div>

        <button className="btn-primary">Save Privacy Settings</button>
      </div>
    </Card>
  )
}

function SecuritySettings() {
  return (
    <Card title="Security Settings">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Two-factor authentication</h4>
            <p className="text-sm text-gray-600">Add an extra layer of security</p>
          </div>
          <button className="btn-secondary">Enable 2FA</button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Encryption</h4>
            <p className="text-sm text-gray-600">Encrypt all your data</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" defaultChecked />
        </div>

        <div>
          <label className="label">Change Password</label>
          <input type="password" placeholder="Current password" className="input mb-3" />
          <input type="password" placeholder="New password" className="input mb-3" />
          <input type="password" placeholder="Confirm new password" className="input" />
        </div>

        <button className="btn-primary">Update Security Settings</button>
      </div>
    </Card>
  )
}

function NotificationSettings() {
  return (
    <Card title="Notification Preferences">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Email notifications</h4>
            <p className="text-sm text-gray-600">Receive email alerts for violations</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" defaultChecked />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Privacy insights</h4>
            <p className="text-sm text-gray-600">Get weekly privacy insights</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" defaultChecked />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Compliance alerts</h4>
            <p className="text-sm text-gray-600">Notify me of compliance issues</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" defaultChecked />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900">Data deletion reminders</h4>
            <p className="text-sm text-gray-600">Remind me before scheduled deletions</p>
          </div>
          <input type="checkbox" className="w-5 h-5 text-primary-600" defaultChecked />
        </div>

        <button className="btn-primary">Save Notification Settings</button>
      </div>
    </Card>
  )
}
