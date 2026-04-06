import streamlit as st
import math
import random
import os
import time
from PIL import Image, ImageDraw

st.set_page_config(page_title="TD D&D Streamlit", layout="wide")

# --- Configuration & Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 700
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_pil_image(filepath, scale=4):
    try:
        # Ensure we use absolute path relative to the script
        if not os.path.isabs(filepath):
            filepath = os.path.join(BASE_DIR, filepath)
        img = Image.open(filepath).convert("RGBA")
        return img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    except Exception as e:
        return Image.new("RGBA", (50 * scale, 50 * scale), (255, 0, 255, 128))

# --- Helper Classes ---
class RectLike:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    @property
    def left(self): return self.x
    @left.setter
    def left(self, v): self.x = v
    @property
    def top(self): return self.y
    @top.setter
    def top(self, v): self.y = v
    @property
    def centerx(self): return self.x + self.w / 2
    @property
    def center(self): return (self.x + self.w / 2, self.y + self.h / 2)
    @property
    def topleft(self): return (self.x, self.y)
    @topleft.setter
    def topleft(self, v): self.x, self.y = v

# --- Systems & Decorators ---
def hero_trait(trait_name, buff_range, damage_boost):
    def decorator(cls):
        cls.trait_name = trait_name
        cls.buff_range = buff_range
        cls.damage_boost = damage_boost
        
        def apply_trait(self, allies):
            for ally in allies:
                dist = math.hypot(self.pos[0] - ally.pos[0], self.pos[1] - ally.pos[1])
                if dist <= self.buff_range:
                    ally.bonus_damage = max(ally.bonus_damage, getattr(self, "damage_boost", 0))
        cls.apply_trait = apply_trait
        return cls
    return decorator

RACE_STATS = {
    "Human": {"hp": 100, "attack_speed": 1.0, "attack_damage": 10},
    "Elf": {"hp": 80, "attack_speed": 1.5, "attack_damage": 8},
    "Dwarf": {"hp": 120, "attack_speed": 0.8, "attack_damage": 12},
    "Orc": {"hp": 150, "attack_speed": 0.5, "attack_damage": 15},
    "Tiefling": {"hp": 90, "attack_speed": 1.2, "attack_damage": 11},
    "Halfling": {"hp": 70, "attack_speed": 1.8, "attack_damage": 6}
}

CLASS_STATS = {
    "Fighter": {"range": 100, "cooldown": 60, "targets": 1},
    "Wizard": {"range": 300, "cooldown": 120, "targets": 3},
    "Barbarian": {"range": 80, "cooldown": 90, "targets": 2},
    "Cleric": {"range": 200, "cooldown": 80, "targets": 1},
    "Paladin": {"range": 120, "cooldown": 70, "targets": 1},
    "Rogue": {"range": 90, "cooldown": 40, "targets": 1},
    "Ranger": {"range": 350, "cooldown": 80, "targets": 1},
    "Bard": {"range": 150, "cooldown": 100, "targets": 2}
}

class GameState:
    CAMP = "camp"
    ADVENTURE = "adventure"
    HERO_PROFILE = "hero_profile"

class Hero:
    def __init__(self, name, hero_class, hero_race, pos):
        self.name = name
        self.hero_class = hero_class 
        self.hero_race = hero_race 
        self.pos = list(pos)
        
        r_stats = RACE_STATS.get(hero_race, RACE_STATS["Human"])
        self.hp = r_stats["hp"]
        self.max_hp = self.hp
        self.attack_speed = r_stats["attack_speed"]
        self.attack_damage = r_stats["attack_damage"]
        
        c_stats = CLASS_STATS.get(hero_class, CLASS_STATS["Fighter"])
        self.attack_range = c_stats["range"]
        self.cooldown = c_stats["cooldown"]
        self.targets = c_stats["targets"]
        self.current_cooldown = 0
        self.active_in_wave = True
        
        self.rect = RectLike(pos[0], pos[1], 48, 64)
        
        self.image_1 = load_pil_image(os.path.join("assets", "heroes", f"{self.name}_1.png"))
        self.image_2 = load_pil_image(os.path.join("assets", "heroes", f"{self.name}_2.png"))
        
    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0

@hero_trait("Inspiring Presence", 150, 5)
class FighterHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Fighter", hero_race, pos)

@hero_trait("Arcane Aura", 300, 10)
class WizardHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Wizard", hero_race, pos)

@hero_trait("Rage Aura", 100, 15)
class BarbarianHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Barbarian", hero_race, pos)

@hero_trait("Blessing", 200, 5)
class ClericHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Cleric", hero_race, pos)

@hero_trait("Holy Aura", 150, 10)
class PaladinHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Paladin", hero_race, pos)

@hero_trait("Shadow Step", 100, 5)
class RogueHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Rogue", hero_race, pos)

@hero_trait("Eagle Eye", 250, 5)
class RangerHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Ranger", hero_race, pos)

@hero_trait("Song of Courage", 300, 8)
class BardHero(Hero):
    def __init__(self, name, hero_race, pos):
        super().__init__(name, "Bard", hero_race, pos)

class Ally:
    def __init__(self, name, pos, ally_type="squire"):
        self.name = name
        self.pos = list(pos)
        self.ally_type = ally_type
        self.rect = RectLike(self.pos[0], self.pos[1], 48, 64)
        self.image = load_pil_image(os.path.join("assets", "allies", f"hero_{self.ally_type}.png"))
        self.base_damage = 10
        self.bonus_damage = 0
        self.attack_range = 150
        self.current_cooldown = 0
        self.retreating = False
        
    def get_damage(self):
        return self.base_damage + self.bonus_damage
        
    def update(self):
        if self.retreating:
            self.pos[0] += 5
            self.rect.left = int(self.pos[0])

class Projectile:
    def __init__(self, pos, target_enemy, damage, color="yellow"):
        self.pos = list(pos)
        self.target = target_enemy
        self.damage = damage
        self.speed = 10
        self.color = color
        self.hit = False

    def update(self, log):
        if not self.target or self.target.hp <= 0:
            self.hit = True
            return
            
        dx = self.target.pos[0] - self.pos[0]
        dy = self.target.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        
        if dist < self.speed:
            self.target.hp -= self.damage
            if self.target.hp <= 0:
                self.target.hp = 0
                log.append(f"Enemy {self.target.type_name} died!")
            self.hit = True
        else:
            self.pos[0] += dx / dist * self.speed
            self.pos[1] += dy / dist * self.speed

class Enemy:
    def __init__(self, path, type_name="goblin", wave_num=1, is_boss=False):
        self.path = path 
        self.path_index = 0
        self.pos = list(self.path[0])
        self.type_name = type_name
        self.rect = RectLike(self.pos[0], self.pos[1], 48, 64)
        self.speed = 2 + (wave_num * 0.2)
        self.max_hp = 50 + (wave_num * 10)
        self.hp = self.max_hp
        self.damage = 10 + (wave_num * 2)
        self.reached_end = False
        self.is_boss = is_boss
        
        self.image_1 = load_pil_image(os.path.join("assets", "enemies", f"{self.type_name}_1.png"))
        self.image_2 = load_pil_image(os.path.join("assets", "enemies", f"{self.type_name}_2.png"))
        self.anim_timer = 0
        
        if self.is_boss:
            self.max_hp *= 10
            self.hp = self.max_hp
            self.damage *= 5
            self.speed *= 0.5
            self.rect = RectLike(self.pos[0], self.pos[1], 96, 128)
            self.image_1 = self.image_1.resize((96, 128), Image.NEAREST)
            self.image_2 = self.image_2.resize((96, 128), Image.NEAREST)

    def move(self):
        self.anim_timer += 1
        if self.path_index < len(self.path) - 1:
            target = self.path[self.path_index + 1]
            dx = target[0] - self.pos[0]
            dy = target[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist <= self.speed:
                self.pos = list(target)
                self.path_index += 1
            else:
                self.pos[0] += dx / dist * self.speed
                self.pos[1] += dy / dist * self.speed
            self.rect.topleft = (int(self.pos[0]), int(self.pos[1]))
        else:
            self.reached_end = True

class WaveManager:
    def __init__(self, paths):
        self.paths = paths
        self.wave_number = 1
        self.enemies = []
        self.spawn_timer = 0
        self.spawn_delay = 60 
        self.enemies_to_spawn = 0
        self.wave_active = False

    def start_wave(self, log):
        self.wave_active = True
        self.enemies_to_spawn = 10 + (self.wave_number * 5)
        self.spawn_timer = 0
        log.append(f"Wave {self.wave_number} started! Enemies to spawn: {self.enemies_to_spawn}")

    def update(self, party, log):
        if self.wave_active:
            if self.enemies_to_spawn > 0:
                self.spawn_timer += 1
                if self.spawn_timer >= self.spawn_delay:
                    self.spawn_timer = 0
                    self.enemies_to_spawn -= 1
                    valid_paths = [self.paths[i] for i, h in enumerate(party) if h.hp > 0]
                    if valid_paths:
                        chosen_path = random.choice(valid_paths)
                        e_type = random.choice(["goblin", "skeleton"])
                        boss_trigger = (self.wave_number % 10 == 0) and (self.enemies_to_spawn == 0)
                        self.enemies.append(Enemy(chosen_path, type_name=e_type, wave_num=self.wave_number, is_boss=boss_trigger))
            elif len(self.enemies) == 0:
                self.wave_active = False
                self.wave_number += 1
                log.append(f"Wave cleared! Advancing to Wave {self.wave_number}.")
                
        for enemy in self.enemies[:]:
            enemy.move()
            if enemy.reached_end:
                end_pos = enemy.path[-1]
                for hero in party:
                    if hero.pos == [end_pos[0], end_pos[1] - 25] or hero.pos == (end_pos[0], end_pos[1] - 25):
                        hero.take_damage(enemy.damage)
                        log.append(f"{hero.name} was hit by {enemy.type_name} for {enemy.damage} damage! HP: {hero.hp}/{hero.max_hp}")
                        break
                self.enemies.remove(enemy)

class GameEngine:
    def __init__(self):
        self.state = GameState.CAMP
        self.party = [
            FighterHero("Aric", "Human", (850, 100)),
            WizardHero("Luna", "Elf", (850, 250)),
            BarbarianHero("Grog", "Orc", (850, 400)),
            ClericHero("Zilar", "Dwarf", (850, 550)),
            PaladinHero("Theron", "Human", (850, 100)),
            RogueHero("Elara", "Elf", (850, 100)),
            RangerHero("Sylas", "Halfling", (850, 100)),
            BardHero("Finny", "Tiefling", (850, 100))
        ]
        
        for hero in self.party[4:]:
            hero.active_in_wave = False
        
        self.paths = [
            [(50, 125), (400, 125), (850, 125)],
            [(50, 275), (400, 275), (850, 275)],
            [(50, 425), (400, 425), (850, 425)],
            [(50, 575), (400, 575), (850, 575)]
        ]
        
        active_party = [h for h in self.party if h.active_in_wave]
        for idx, hero in enumerate(active_party[:4]):
            hero.pos = [850, self.paths[idx][-1][1] - 25]
            hero.rect.topleft = tuple(hero.pos)
        
        self.wave_manager = WaveManager(self.paths)
        self.allies = []
        self.mana = 100
        self.gold = 0
        self.projectiles = []
        self.profile_hero_index = 0
        self.hard_mode = False
        self.simulation_logs = []

    def run_simulation_step(self):
        active_party = [h for h in self.party if h.active_in_wave]
        self.wave_manager.update(active_party, self.simulation_logs)
        
        for hero in active_party:
            if hero.hp <= 0:
                for ally in self.allies:
                    if abs(ally.rect.top - (hero.rect.top - 60)) < 20:
                        ally.retreating = True

        for ally in self.allies[:]:
            ally.update()
            if ally.pos[0] > SCREEN_WIDTH:
                self.allies.remove(ally)
            
        if self.wave_manager.wave_active:
            for hero in active_party:
                if hasattr(hero.__class__, 'apply_trait'):
                    hero.apply_trait(self.allies)
                if hero.hp > 0:
                    if hero.current_cooldown > 0:
                        hero.current_cooldown -= 1
                    else:
                        for enemy in self.wave_manager.enemies:
                            dist = math.hypot(hero.pos[0] - enemy.pos[0], hero.pos[1] - enemy.pos[1])
                            if dist <= hero.attack_range:
                                self.projectiles.append(Projectile(hero.rect.center, enemy, hero.attack_damage, "cyan"))
                                hero.current_cooldown = hero.cooldown
                                break
                                
            for ally in self.allies:
                if getattr(ally, 'retreating', False):
                    continue
                if ally.current_cooldown > 0:
                    ally.current_cooldown -= 1
                else:
                    for enemy in self.wave_manager.enemies:
                        dist = math.hypot(ally.pos[0] - enemy.pos[0], ally.pos[1] - enemy.pos[1])
                        if dist <= ally.attack_range:
                            self.projectiles.append(Projectile(ally.rect.center, enemy, ally.get_damage(), "orange"))
                            ally.current_cooldown = 60
                            break
        
        for proj in self.projectiles[:]:
            proj.update(self.simulation_logs)
            if proj.hit:
                self.projectiles.remove(proj)
        
        self.wave_manager.enemies = [e for e in self.wave_manager.enemies if e.hp > 0]
            
        if len(active_party) > 0 and all(hero.hp == 0 for hero in active_party):
            self.state = GameState.CAMP
            self.wave_manager.wave_active = False
            self.wave_manager.enemies.clear()
            self.projectiles.clear()
            self.simulation_logs.append("All heroes defeated! Returning to Camp...")


# === Frame Rendering for Animation ===
def render_frame(eng):
    base = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (34, 139, 34)) # Green background
    draw = ImageDraw.Draw(base)
    
    # Draw paths
    for path in eng.paths:
        draw.line([tuple(p) for p in path], fill=(100, 100, 100), width=20)
        
    # Draw enemies
    for enemy in eng.wave_manager.enemies:
        img = enemy.image_1 if (enemy.anim_timer // 15) % 2 == 0 else enemy.image_2 
        base.paste(img, (int(enemy.rect.x), int(enemy.rect.y)), img)
        hp_ratio = enemy.hp / enemy.max_hp
        draw.rectangle([enemy.rect.x, enemy.rect.y-10, enemy.rect.x+30, enemy.rect.y-5], fill=(0,0,0))
        draw.rectangle([enemy.rect.x, enemy.rect.y-10, enemy.rect.x+30*hp_ratio, enemy.rect.y-5], fill=(0,255,0))
        
    # Draw allies
    for ally in eng.allies:
        base.paste(ally.image, (int(ally.rect.x), int(ally.rect.y)), ally.image)
        
    # Draw heroes
    active_party = [h for h in eng.party if h.active_in_wave]
    for hero in active_party:
        img = hero.image_2 if hero.current_cooldown > hero.cooldown - 10 else hero.image_1
        base.paste(img, (int(hero.rect.x), int(hero.rect.y)), img)
        hp_ratio = hero.hp / hero.max_hp
        draw.rectangle([hero.rect.x, hero.rect.y-10, hero.rect.x+50, hero.rect.y-5], fill=(255,0,0))
        draw.rectangle([hero.rect.x, hero.rect.y-10, hero.rect.x+50*hp_ratio, hero.rect.y-5], fill=(0,255,0))
        
    # Draw projectiles
    for proj in eng.projectiles:
        # map color strings to tuples if needed, PIL supports common color strings though
        draw.ellipse([proj.pos[0]-5, proj.pos[1]-5, proj.pos[0]+5, proj.pos[1]+5], fill=proj.color)
        
    return base


# === Streamlit UI Rendering ===

def init_game():
    if "engine" not in st.session_state:
        st.session_state.engine = GameEngine()

def draw_camp():
    st.header("🏕️ The Camp")
    eng = st.session_state.engine
    
    active_count = len([h for h in eng.party if h.active_in_wave])
    st.write(f"**Gold:** 🪙 {eng.gold}  |  **Mana:** 🔮 {eng.mana}  |  **Mode:** {'Hard' if eng.hard_mode else 'Easy'}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Adventure", disabled=active_count == 0 or active_count > 4):
            eng.state = GameState.ADVENTURE
            eng.allies.clear()
            eng.simulation_logs.clear()
            if not eng.hard_mode:
                eng.wave_manager.wave_number = 1
            
            active_heroes = [h for h in eng.party if h.active_in_wave]
            for idx, hero in enumerate(active_heroes):
                hero.pos = [850, eng.paths[idx][-1][1] - 25]
                hero.rect.topleft = tuple(hero.pos)
            st.rerun()
            
    with col2:
        if st.button("Rest (Restore HP)"):
            for hero in eng.party:
                hero.hp = hero.max_hp
            st.success("All heroes fully healed!")
            
    eng.hard_mode = st.checkbox("Hard Mode (Continuous Waves)", value=eng.hard_mode)
    
    st.divider()
    st.subheader("Party Roster")
    
    for i in range(0, len(eng.party), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(eng.party):
                hero = eng.party[i + j]
                with col:
                    st.image(hero.image_1, width=48)
                    st.markdown(f"**{hero.name}**")
                    st.write(f"*{hero.hero_class} ({hero.hero_race})*")
                    st.write(f"HP: {hero.hp}/{hero.max_hp} | DMG: {hero.attack_damage}")
                    hero.active_in_wave = st.checkbox(f"Active", value=hero.active_in_wave, key=f"active_{hero.name}")
                    
                    if st.button("View Profile", key=f"profile_{hero.name}"):
                        eng.profile_hero_index = eng.party.index(hero)
                        eng.state = GameState.HERO_PROFILE
                        st.rerun()

def draw_hero_profile():
    st.header("👤 Hero Profile")
    eng = st.session_state.engine
    hero = eng.party[eng.profile_hero_index]
    
    if st.button("⬅️ Back to Camp"):
        eng.state = GameState.CAMP
        st.rerun()
        
    st.subheader(f"{hero.name} - {hero.hero_race} {hero.hero_class}")
    st.write(f"**Gold:** {eng.gold}")
    
    st.image(hero.image_1, width=96)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Damage:** {hero.attack_damage}")
        if st.button("+5 DMG (50G)", disabled=eng.gold < 50):
            eng.gold -= 50
            hero.attack_damage += 5
            st.rerun()
            
        st.write(f"**Health:** {hero.hp}/{hero.max_hp}")
        if st.button("+20 HP (50G)", disabled=eng.gold < 50):
            eng.gold -= 50
            hero.max_hp += 20
            hero.hp += 20
            st.rerun()
            
    with col2:
        st.write(f"**Range:** {hero.attack_range}")
        if st.button("+20 Range (50G)", disabled=eng.gold < 50):
            eng.gold -= 50
            hero.attack_range += 20
            st.rerun()
            
        st.write(f"**Cooldown:** {hero.cooldown}")
        if st.button("-5 Cooldown (50G)", disabled=eng.gold < 50 or hero.cooldown <= 10):
            eng.gold -= 50
            hero.cooldown -= 5
            st.rerun()

def draw_adventure():
    st.header("🗺️ The Adventure")
    eng = st.session_state.engine
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Wave:** {eng.wave_manager.wave_number} | **Gold:** {eng.gold} | **Mana:** {eng.mana}")
    with col2:
        if st.button("🏕️ Retreat"):
            eng.state = GameState.CAMP
            eng.wave_manager.wave_active = False
            eng.wave_manager.enemies.clear()
            eng.projectiles.clear()
            st.rerun()
            
    st.divider()
    
    st.subheader("Battle Canvas")
    canvas_placeholder = st.empty()
    
    if not eng.wave_manager.wave_active:
        canvas_placeholder.image(render_frame(eng), use_container_width=True)
        if st.button("⚔️ Start Animated Wave", type="primary"):
            eng.wave_manager.start_wave(eng.simulation_logs)
            
            try:
                # Inline Animation Loop
                # We cap the loop with a safety timeout (e.g., 120 seconds per wave max)
                start_loop_time = time.time()
                while eng.wave_manager.wave_active and (time.time() - start_loop_time < 120):
                    # Step the logic twice per render (approx 60 logic ticks / sec at 33ms sleep)
                    eng.run_simulation_step()
                    eng.run_simulation_step()
                    
                    frame = render_frame(eng)
                    canvas_placeholder.image(frame, use_container_width=True)
                    # Slowing down to 30fps to avoid overloading Streamlit Cloud WebSocket
                    time.sleep(0.033)
                    
                # Explicitly check for wave completion
                if not eng.wave_manager.wave_active:
                    # Award rewards after successful completion
                    reward_gold = (eng.wave_manager.wave_number - 1) * 50
                    eng.gold += reward_gold
                    eng.mana += 50
                    eng.simulation_logs.append(f"VICTORY! Awarded {reward_gold} Gold and 50 Mana.")
                    st.success(f"Wave Cleared! +{reward_gold} Gold")
                    time.sleep(1) # Let user see the success
            except Exception as e:
                st.error(f"Interaction Error during Wave: {str(e)}")
                # Break out of wave state to recover app
                eng.wave_manager.wave_active = False 
            
            st.rerun()
    else:
        # If mid-wave due to a weird refresh, keep showing the frame
        canvas_placeholder.image(render_frame(eng), use_container_width=True)
                
    st.subheader("Active Party Status")
    cols = st.columns(4)
    active_party = [h for h in eng.party if h.active_in_wave]
    for i, hero in enumerate(active_party):
        with cols[i % 4]:
            st.write(f"**{hero.name}**: {hero.hp}/{hero.max_hp} HP")
            if st.button(f"Summon Ally (20 Mana)", disabled=eng.mana < 20 or hero.hp <= 0, key=f"sum_{hero.name}"):
                eng.mana -= 20
                a_type = random.choice(["squire", "acolyte", "apprentice"])
                row_allies = [a for a in eng.allies if abs(a.rect.top - (hero.rect.top - 60)) < 20]
                if len(row_allies) < 5:
                    offset = (len(row_allies) + 1) * 60
                    new_pos = [hero.rect.left - offset, hero.rect.top - 60]
                    eng.allies.append(Ally(f"{hero.hero_class} Minion", new_pos, ally_type=a_type))
                st.rerun()
                
    st.subheader("Simulation Logs")
    if eng.simulation_logs:
        for log in reversed(eng.simulation_logs[-15:]):
            st.text(log)
    else:
        st.write("No action yet.")

def main():
    init_game()
    eng = st.session_state.engine
    
    if eng.state == GameState.CAMP:
        draw_camp()
    elif eng.state == GameState.HERO_PROFILE:
        draw_hero_profile()
    elif eng.state == GameState.ADVENTURE:
        draw_adventure()

if __name__ == "__main__":
    main()
