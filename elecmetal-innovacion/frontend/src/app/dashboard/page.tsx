"use client";

import { useProfile, useInitiatives } from "@/lib/hooks";
import Link from "next/link";

export default function DashboardPage() {
  const { data: profile, isLoading: profileLoading } = useProfile();
  const { data: initiatives = [], isLoading: initiativesLoading } =
    useInitiatives();

  const loading = profileLoading || initiativesLoading;

  return (
    <div className="space-y-6 p-8">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Profile card */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        {profileLoading ? (
          <p className="text-sm text-gray-400">Cargando perfil…</p>
        ) : profile ? (
          <>
            <p className="text-sm text-gray-600">
              Bienvenido,{" "}
              <span className="font-medium text-gray-900">
                {profile.full_name}
              </span>
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Rol: {profile.role || "postulante"}
            </p>
          </>
        ) : (
          <p className="text-sm text-gray-400">
            No se pudo cargar el perfil.
          </p>
        )}
      </div>

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
            {initiatives.map((init: {
              id: number;
              initiative_code: string;
              title: string;
              status: string;
              initiative_type: string;
              created_at: string;
            }) => (
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
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        {init.status}
                      </span>
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
      ) : (
        <div className="rounded-lg border bg-white p-8 text-center">
          <p className="text-sm text-gray-500">
            No tienes iniciativas todavia.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Inicia una conversacion con Clara desde el sidebar para postular
            tu primera iniciativa.
          </p>
        </div>
      )}
    </div>
  );
}
