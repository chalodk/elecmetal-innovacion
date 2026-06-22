"use client";

import { useProfile } from "@/hooks/use-profile";
import { useSessions } from "@/hooks/use-sessions";
import { useInitiatives } from "@/hooks/use-initiatives";
import ProfileCard from "@/components/dashboard/profile-card";
import WelcomeState from "@/components/dashboard/welcome-state";
import StatusBadge from "@/components/ui/StatusBadge";
import Link from "next/link";

export default function DashboardPage() {
  const { data: profile, isLoading: profileLoading } = useProfile();
  const { data: sessions = [] } = useSessions();
  const { data: initiativesData, isLoading: initiativesLoading } =
    useInitiatives();

  const initiatives = initiativesData?.data ?? [];
  const loading = profileLoading || initiativesLoading;

  return (
    <div className="space-y-6 p-8">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Profile card — Diego's component */}
      {profileLoading ? (
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-400">Cargando perfil…</p>
        </div>
      ) : profile ? (
        <ProfileCard fullName={profile.full_name} role={profile.role} />
      ) : null}

      {/* Welcome / empty state — Diego's component */}
      {!loading && initiatives.length === 0 && (
        <WelcomeState hasSessions={sessions.length > 0} />
      )}

      {/* Initiatives section */}
      {loading ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <p className="text-sm text-gray-400">Cargando iniciativas…</p>
        </div>
      ) : initiatives.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800">
            Mis Iniciativas
          </h2>
          <div className="space-y-2">
            {initiatives.map((init: typeof initiatives[number]) => (
              <Link
                key={init.id}
                href={`/dashboard/initiatives/${init.id}`}
                className="block rounded-lg border bg-white p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-gray-400">
                        {init.initiative_code}
                      </span>
                      <StatusBadge status={init.status} />
                      <span className="text-xs text-gray-400 capitalize">
                        {init.initiative_type}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {init.title}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400 flex-shrink-0 ml-4">
                    {new Date(init.created_at).toLocaleDateString("es-CL")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
