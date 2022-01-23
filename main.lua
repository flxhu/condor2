TEXTURE_MATERIAL = {}
CANVAS_X = 5
CANVAS_Y = 5
OFFSET_X = 0
OFFSET_Y = 0
MAX_X = 55
MAX_Y = 87

box = {
  position = lovr.math.newVec3(0, 0, 0),
}
  
drag = {
  active = false,
  hand = nil,
  offset = lovr.math.newVec3()
}

-- mklink.exe /J Textures ..\..\Textures

function lovr.textinput(text, code)
  print(text)

  changed = false
  if text == 'a' and OFFSET_X < (MAX_X - CANVAS_X) then
    OFFSET_X = OFFSET_X + 1
    changed = true
  end
  if text == 'd' and OFFSET_X > 0 then
    OFFSET_X = OFFSET_X - 1
    changed = true
  end
  if text == 's' and OFFSET_Y < (MAX_Y - CANVAS_Y) then
    OFFSET_Y = OFFSET_Y + 1
    changed = true
  end
  if text == 'w' and OFFSET_Y > 0 then
    OFFSET_Y = OFFSET_Y - 1
    changed = true
  end
  
  if text == "A" then
    OFFSET_X = MAX_X - CANVAS_X
    changed = true
  end 
  if text == "D" then
    OFFSET_X = 0
    changed = true
  end 
  if text == "S" then
    OFFSET_Y = MAX_Y - CANVAS_Y
    changed = true
  end 
  if text == "W" then
    OFFSET_Y = 0
    changed = true
  end 

  if changed then
    for x = 0, CANVAS_X do
      for y = 0, CANVAS_Y do
        coord = string.format("%02d%02d", x, y)
        moved = string.format("%02d%02d", x + OFFSET_X, y + OFFSET_Y)
        print(coord)
        -- texture = lovr.graphics.newTexture(
        --    string.format("t%s.dds", coord))
        texture = lovr.graphics.newTexture(
           string.format("Textures/t%s.dds", moved))
        
        material = lovr.graphics.newMaterial(texture)
        TEXTURE_MATERIAL[coord] = material
      end
    end
  end
end

function lovr.update(dt)
  
  if not drag.active then
    for i, hand in ipairs(lovr.headset.getHands()) do
      if lovr.headset.isDown(hand, 'trigger') then
        local offset = box.position - vec3(lovr.headset.getPosition(hand))
        drag.active = true
        drag.hand = hand
        drag.offset:set(offset)
        print(drag.offset)
      end
    end
  end

  if drag.active then
    local handPosition = vec3(lovr.headset.getPosition(drag.hand))
    box.position:set(handPosition + drag.offset)

    if not lovr.headset.isDown(drag.hand, 'trigger') then
      drag.active = false
    end
  end
end

function lovr.load()
  for x = 0, CANVAS_X do
    for y = 0, CANVAS_Y do
      coord = string.format("%02d%02d", x, y)
      print(coord)
      -- texture = lovr.graphics.newTexture(
      --    string.format("t%s.dds", coord))
      texture = lovr.graphics.newTexture(
         string.format("Textures/t%s.dds", coord))
      
      material = lovr.graphics.newMaterial(texture)
      TEXTURE_MATERIAL[coord] = material
    end
  end
end

function lovr.draw()
  lovr.graphics.setBackgroundColor(.5, .5, .95)
  lovr.graphics.setShader(shader)

  lovr.graphics.print(string.format("%s %s %s", box.position, drag.offset, drag.active), 0, 1.7, -3, .2)

  for i, hand in ipairs(lovr.headset.getHands()) do
    lovr.graphics.setColor(lovr.headset.isDown(hand, 'trigger') and 0xffffff or 0x050505)
    lovr.graphics.cube('fill', mat4(lovr.headset.getPose(hand)):scale(.01))
  end

  lovr.graphics.translate(box.position)
  lovr.graphics.setColor(1, 1, 1)
  for x = 0, CANVAS_X do
    for y = 0, CANVAS_Y do
      coord = string.format("%02d%02d", x, y)
      absolute = string.format("%02d%02d", x + OFFSET_X, y + OFFSET_Y)
      lovr.graphics.print(absolute, -x + 2.5, -y + 2.5, -1.9, .1)
      lovr.graphics.plane(TEXTURE_MATERIAL[coord], -x + 2.5, -y + 2.5, -2, 1, 1)
    end
  end
end
