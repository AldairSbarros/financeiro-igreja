"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api"; // Import do cliente de API

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();
  const [setupRequired, setSetupRequired] = useState<boolean | null>(null); // null = carregando
  const [loadingSetup, setLoadingSetup] = useState(true);

  useEffect(() => {
    const checkSetupStatus = async () => {
      try {
        const response = await api.get("/setup/status");
        if (!response.data.setup_complete) {
          setSetupRequired(true);
          router.push("/setup");
        } else {
          setSetupRequired(false);
        }
      } catch (error) {
        console.error("Erro ao verificar status do setup:", error);
        toast.error("Erro ao verificar status inicial do sistema.");
      } finally {
        setLoadingSetup(false);
      }
    };
    checkSetupStatus();
  }, [router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, password);
      toast.success("Login realizado com sucesso!");
      
      // Redireciona appropriately based on user role
      // You might want to fetch user details from the auth context to check is_superuser
      router.push("/dashboard"); // For now, redirect to dashboard. We can refine this.
    } catch (error) {
      toast.error("Email ou senha inválidos.");
    } finally {
      setIsLoading(false);
    }
  };

  if (loadingSetup || setupRequired === null) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-slate-950">
        <p className="text-white">Carregando status do sistema...</p>
      </main>
    );
  }

  // Se o setup for necessário e já fomos redirecionados, não renderiza o formulário de login
  if (setupRequired) {
    return null;
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-slate-950">
      <Card className="w-full max-w-sm bg-slate-900 border-slate-800 text-white">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Painel Financeiro</CardTitle>
          <CardDescription>Acesse com suas credenciais</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                  id="email"
                  type="email"
                  placeholder="seu.email@exemplo.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-slate-800 border-slate-700 focus:ring-emerald-500"
                />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-slate-800 border-slate-700 focus:ring-emerald-500"
                />
            </div>
            <Button type="submit" className="w-full mt-2 bg-emerald-600 hover:bg-emerald-500" disabled={isLoading}>
              {isLoading ? "Verificando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
