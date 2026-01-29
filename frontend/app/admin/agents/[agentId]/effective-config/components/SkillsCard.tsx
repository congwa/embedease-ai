"use client";

import { Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { EffectiveConfigResponse, SkillInfo } from "@/lib/api/agents";

interface SkillsCardProps {
  skills: EffectiveConfigResponse["skills"];
}

export function SkillsCard({ skills }: SkillsCardProps) {
  const totalSkills = skills.always_apply.length + skills.conditional.length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-500" />
          <CardTitle className="text-base">技能清单</CardTitle>
          <Badge variant="secondary">{totalSkills} 个</Badge>
        </div>
        <CardDescription>已配置的技能列表</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="always" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="always">
              始终生效 ({skills.always_apply.length})
            </TabsTrigger>
            <TabsTrigger value="conditional">
              条件触发 ({skills.conditional.length})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="always" className="mt-4 space-y-2">
            {skills.always_apply.length === 0 ? (
              <p className="text-sm text-muted-foreground">无始终生效技能</p>
            ) : (
              skills.always_apply.map((skill) => <SkillItem key={skill.id} skill={skill} type="always" />)
            )}
          </TabsContent>
          <TabsContent value="conditional" className="mt-4 space-y-2">
            {skills.conditional.length === 0 ? (
              <p className="text-sm text-muted-foreground">无条件触发技能</p>
            ) : (
              skills.conditional.map((skill) => <SkillItem key={skill.id} skill={skill} type="conditional" />)
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function SkillItem({ skill, type }: { skill: SkillInfo; type: "always" | "conditional" }) {
  return (
    <div className="rounded-md border p-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${type === "always" ? "bg-green-500" : "bg-yellow-500"}`}
          />
          <span className="font-medium">{skill.name}</span>
        </div>
        <Badge variant="outline">优先级: {skill.priority}</Badge>
      </div>
      {skill.description && (
        <p className="mt-1 text-sm text-muted-foreground">{skill.description}</p>
      )}
      {type === "conditional" && skill.trigger_keywords.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {skill.trigger_keywords.slice(0, 5).map((kw, i) => (
            <Badge key={i} variant="secondary" className="text-xs">
              {kw}
            </Badge>
          ))}
          {skill.trigger_keywords.length > 5 && (
            <Badge variant="secondary" className="text-xs">
              +{skill.trigger_keywords.length - 5}
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
